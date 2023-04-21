import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';

interface IProps extends StackProps {
  readonly cluster: ecs.ICluster;
  readonly taskRole: iam.IRole;
  readonly taskLogGroup: logs.ILogGroup;
  readonly taskExecutionRole: iam.IRole;
  readonly taskSecurityGroup: ec2.ISecurityGroup;
}

export class XrayDaemonServiceStack extends Stack {
  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    const taskDefinition = this.newTaskDefinition(props);
    this.newEc2Service(taskDefinition, props);
  }

  private newTaskDefinition(props: IProps): ecs.TaskDefinition {
    const ns = this.node.tryGetContext('ns') as string;

    const taskDefinition = new ecs.Ec2TaskDefinition(this, `TaskDefinition`, {
      networkMode: ecs.NetworkMode.HOST,
      family: `${ns}XrayDaemon`,
      taskRole: props.taskRole,
      executionRole: props.taskExecutionRole,
    });

    const logging = new ecs.AwsLogDriver({
      logGroup: props.taskLogGroup,
      streamPrefix: 'xray',
    });
    taskDefinition.addContainer(`Container`, {
      containerName: 'xray-daemon',
      image: ecs.ContainerImage.fromRegistry(
        'public.ecr.aws/xray/aws-xray-daemon:latest'
      ),
      logging,
      portMappings: [
        { hostPort: 2000, containerPort: 2000, protocol: ecs.Protocol.UDP },
      ],
      cpu: 32,
      memoryReservationMiB: 256,
      environment: {
        AWS_REGION: Stack.of(this).region,
      },
    });

    return taskDefinition;
  }

  private newEc2Service(taskDefinition: ecs.TaskDefinition, props: IProps) {
    const service = new ecs.Ec2Service(this, 'Ec2Service', {
      serviceName: 'xray-daemon',
      cluster: props.cluster,
      circuitBreaker: { rollback: true },
      taskDefinition,
      daemon: true,
    });
    return service;
  }
}
