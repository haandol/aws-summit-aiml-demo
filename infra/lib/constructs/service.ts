import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as efs from 'aws-cdk-lib/aws-efs';
import * as logs from 'aws-cdk-lib/aws-logs';

interface IProps {
  readonly cluster: ecs.ICluster;
  readonly taskRole: iam.IRole;
  readonly taskLogGroup: logs.ILogGroup;
  readonly taskExecutionRole: iam.IRole;
  readonly taskSecurityGroup: ec2.ISecurityGroup;
  readonly taskEnvs: { [key: string]: ecs.Secret };
  readonly fileSystem: efs.IFileSystem;
  readonly service: {
    name: string;
    repositoryName: string;
    port: number;
    tag: string;
  };
}

export class CommonService extends Construct {
  public readonly ecsService: ecs.Ec2Service;

  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id);

    const taskDefinition = this.newTaskDefinition(props);
    this.ecsService = this.newEc2Service(taskDefinition, props);
  }

  private newTaskDefinition(props: IProps): ecs.TaskDefinition {
    const ns = this.node.tryGetContext('ns') as string;

    const accessPoint = new efs.AccessPoint(this, 'AccessPoint', {
      createAcl: {
        ownerUid: '1000',
        ownerGid: '1000',
        permissions: '0777',
      },
      path: '/app/huggingface',
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
      networkMode: ecs.NetworkMode.BRIDGE,
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
      streamPrefix: ns.toLowerCase(),
    });
    taskDefinition.addContainer(`Container`, {
      containerName: props.service.name.toLowerCase(),
      image: ecs.ContainerImage.fromEcrRepository(
        serviceRepository,
        props.service.tag
      ),
      logging,
      healthCheck: {
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

    return taskDefinition;
  }

  private newEc2Service(taskDefinition: ecs.TaskDefinition, props: IProps) {
    const service = new ecs.Ec2Service(this, 'Ec2Service', {
      serviceName: `${props.service.name}`,
      cluster: props.cluster,
      circuitBreaker: { rollback: true },
      taskDefinition,
      desiredCount: 0,
      minHealthyPercent: 0,
      maxHealthyPercent: 100,
      cloudMapOptions: {
        name: props.service.name.toLowerCase(),
        containerPort: props.service.port,
      },
    });

    return service;
  }
}
