import { Stack, StackProps, RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as efs from 'aws-cdk-lib/aws-efs';

interface IProps extends StackProps {
  readonly vpc: ec2.IVpc;
}

export class EfsStack extends Stack {
  public readonly fileSystem: efs.IFileSystem;

  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    this.fileSystem = this.newFileSystem(props);
  }

  newFileSystem(props: IProps): efs.FileSystem {
    const fileSystem = new efs.FileSystem(this, `FileSystem`, {
      vpc: props.vpc,
      encrypted: true,
      performanceMode: efs.PerformanceMode.GENERAL_PURPOSE,
      throughputMode: efs.ThroughputMode.BURSTING,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    fileSystem.connections.allowFrom(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(2049)
    );
    fileSystem.connections.allowInternally(ec2.Port.allTraffic());

    return fileSystem;
  }
}
