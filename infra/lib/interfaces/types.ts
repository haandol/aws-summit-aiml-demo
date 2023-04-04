import { StackProps } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as efs from 'aws-cdk-lib/aws-efs';
import * as logs from 'aws-cdk-lib/aws-logs';

export interface IServiceProps extends StackProps {
  readonly cluster: ecs.ICluster;
  readonly taskRole: iam.IRole;
  readonly taskLogGroup: logs.ILogGroup;
  readonly taskExecutionRole: iam.IRole;
  readonly taskSecurityGroup: ec2.ISecurityGroup;
  readonly taskEnvs?: { [key: string]: ecs.Secret };
  readonly service: {
    name: string;
    repositoryName: string;
    port: number;
    tag: string;
  };
}

export interface IChatbotServiceProps extends IServiceProps {
  readonly fileSystem: efs.IFileSystem;
}
