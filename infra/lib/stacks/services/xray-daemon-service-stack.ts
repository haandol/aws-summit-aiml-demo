import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
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
    taskDefinition.addContainer(`OTelContainer`, {
      containerName: 'aws-otel-collector',
      hostname: 'aws-otel-collector',
      image: ecs.ContainerImage.fromRegistry('amazon/aws-otel-collector'),
      command: ['--config=/etc/ecs/ecs-cloudwatch-xray.yaml'],
      portMappings: [
        { containerPort: 4317, protocol: ecs.Protocol.TCP, hostPort: 4317 },
      ],
      secrets: {
        AWS_REGION: ecs.Secret.fromSsmParameter(
          new ssm.StringParameter(this, 'EnvAwsRegion', {
            stringValue: 'ap-northeast-2',
          })
        ),
      },
      logging,
      cpu: 100,
      memoryReservationMiB: 128,
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
