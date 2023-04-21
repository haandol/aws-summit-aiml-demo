import { Duration } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as efs from 'aws-cdk-lib/aws-efs';
import { IChatbotServiceProps } from '../interfaces/types';

export class ChatbotService extends Construct {
  public readonly ecsService: ecs.IBaseService;

  constructor(scope: Construct, id: string, props: IChatbotServiceProps) {
    super(scope, id);

    const taskDefinition = this.newTaskDefinition(props);
    this.ecsService = this.newEc2Service(taskDefinition, props);
  }

  private newTaskDefinition(props: IChatbotServiceProps): ecs.TaskDefinition {
    const ns = this.node.tryGetContext('ns') as string;

    const accessPoint = new efs.AccessPoint(this, 'AccessPoint', {
      createAcl: {
        ownerUid: '1000',
        ownerGid: '1000',
        permissions: '0777',
      },
      path: '/huggingface',
      posixUser: {
        uid: '1000',
        gid: '1000',
      },
      fileSystem: props.fileSystem,
    });

    const volumeConfig: ecs.Volume = {
      name: 'efs-volume',
      efsVolumeConfiguration: {
        transitEncryption: 'ENABLED',
        fileSystemId: props.fileSystem.fileSystemId,
        authorizationConfig: {
          accessPointId: accessPoint.accessPointId,
          iam: 'ENABLED',
        },
      },
    };

    const taskDefinition = new ecs.Ec2TaskDefinition(this, `TaskDefinition`, {
      networkMode: ecs.NetworkMode.AWS_VPC,
      family: `${ns}${props.service.name}`,
      taskRole: props.taskRole,
      executionRole: props.taskExecutionRole,
      volumes: [volumeConfig],
    });

    // service container
    const serviceRepository = ecr.Repository.fromRepositoryName(
      this,
      `ServiceRepository`,
      props.service.repositoryName
    );
    const logging = new ecs.AwsLogDriver({
      logGroup: props.taskLogGroup,
      streamPrefix: props.service.name,
    });
    const serviceContainer = taskDefinition.addContainer(`Container`, {
      gpuCount: 1,
      containerName: props.service.name.toLowerCase(),
      image: ecs.ContainerImage.fromEcrRepository(
        serviceRepository,
        props.service.tag
      ),
      essential: true,
      logging,
      healthCheck: {
        startPeriod: Duration.seconds(300),
        command: [
          'CMD-SHELL',
          `curl -f http://localhost:${props.service.port}/healthz/ || exit 1`,
        ],
      },
      portMappings: [
        { containerPort: props.service.port, protocol: ecs.Protocol.TCP },
      ],
      memoryReservationMiB: 1024 * 16,
      secrets: props.taskEnvs,
    });
    serviceContainer.addMountPoints({
      containerPath: '/mnt/huggingface',
      sourceVolume: volumeConfig.name,
      readOnly: false,
    });

    return taskDefinition;
  }

  private newEc2Service(
    taskDefinition: ecs.TaskDefinition,
    props: IChatbotServiceProps
  ) {
    const service = new ecs.Ec2Service(this, 'Ec2Service', {
      serviceName: `${props.service.name}`,
      cluster: props.cluster,
      circuitBreaker: { rollback: true },
      taskDefinition,
      desiredCount: 1,
      minHealthyPercent: 50,
      maxHealthyPercent: 200,
      cloudMapOptions: {
        name: props.service.name.toLowerCase(),
        containerPort: props.service.port,
      },
      securityGroups: [props.taskSecurityGroup],
      placementConstraints: [
        ecs.PlacementConstraint.memberOf(
          'attribute:ecs.instance-type =~ g4dn.*'
        ),
      ],
    });

    const scalableTarget = service.autoScaleTaskCount({
      minCapacity: 1,
      maxCapacity: 6,
    });
    scalableTarget.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
    });
    scalableTarget.scaleOnMemoryUtilization('MemoryScaling', {
      targetUtilizationPercent: 70,
    });

    return service;
  }
}
