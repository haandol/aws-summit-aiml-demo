import { Duration } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { IServiceProps } from '../interfaces/types';

export class FrontendService extends Construct {
  public readonly ecsService: ecs.Ec2Service;

  constructor(scope: Construct, id: string, props: IServiceProps) {
    super(scope, id);

    const taskDefinition = this.newTaskDefinition(props);
    this.ecsService = this.newEc2Service(taskDefinition, props);
  }

  private newTaskDefinition(props: IServiceProps): ecs.TaskDefinition {
    const ns = this.node.tryGetContext('ns') as string;

    const taskDefinition = new ecs.Ec2TaskDefinition(this, `TaskDefinition`, {
      networkMode: ecs.NetworkMode.BRIDGE,
      family: `${ns}${props.service.name}`,
      taskRole: props.taskRole,
      executionRole: props.taskExecutionRole,
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
      gpuCount: 1,
      logging,
      healthCheck: {
        startPeriod: Duration.seconds(180),
        command: [
          'CMD-SHELL',
          `curl -f http://localhost:${props.service.port}/healthz/ || exit 1`,
        ],
      },
      portMappings: [
        { containerPort: props.service.port, protocol: ecs.Protocol.TCP },
      ],
      memoryReservationMiB: 1024,
    });

    return taskDefinition;
  }

  private newEc2Service(
    taskDefinition: ecs.TaskDefinition,
    props: IServiceProps
  ) {
    const service = new ecs.Ec2Service(this, 'Ec2Service', {
      serviceName: `${props.service.name}`,
      cluster: props.cluster,
      circuitBreaker: { rollback: true },
      taskDefinition,
      desiredCount: 1,
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
