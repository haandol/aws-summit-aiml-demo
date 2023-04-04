import { Stack, StackProps, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cloudmap from 'aws-cdk-lib/aws-servicediscovery';
import * as autoscaling from 'aws-cdk-lib/aws-autoscaling';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';

interface IProps extends StackProps {
  vpc: ec2.IVpc;
}

export class EcsClusterStack extends Stack {
  public readonly cluster: ecs.ICluster;
  public readonly taskRole: iam.IRole;
  public readonly taskExecutionRole: iam.IRole;
  public readonly taskLogGroup: logs.ILogGroup;
  public readonly taskSecurityGroup: ec2.ISecurityGroup;
  public readonly alb: elbv2.IApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    this.taskRole = this.newEcsTaskRole().withoutPolicyUpdates();
    this.taskExecutionRole =
      this.newEcsTaskExecutionRole().withoutPolicyUpdates();
    this.taskSecurityGroup = this.newSecurityGroup(props);
    this.taskLogGroup = this.newEcsTaskLogGroup();

    const launchTemplate = this.newLaunchTemplate(this.taskSecurityGroup);
    this.cluster = this.newEcsCluster(props, launchTemplate);

    this.alb = this.newApplicationLoadBalancer(props, this.taskSecurityGroup);
  }

  newLaunchTemplate(securityGroup: ec2.ISecurityGroup): ec2.LaunchTemplate {
    const role = new iam.Role(this, 'LaunchTemplateRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonEC2RoleforSSM'
        ),
      ],
    });

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config',
      'echo ECS_NVIDIA_RUNTIME=nvidia >> /etc/ecs/ecs.config'
    );
    const launchTemplate = new ec2.LaunchTemplate(this, 'LaunchTemplate', {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.P3,
        ec2.InstanceSize.XLARGE8
      ),
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(64, {
            volumeType: ec2.EbsDeviceVolumeType.GP2,
            encrypted: true,
          }),
        },
      ],
      machineImage: ec2.MachineImage.lookup({
        name: 'amzn2-ami-ecs-gpu-hvm-2.0.20230321-x86_64-ebs',
      }),
      userData,
      detailedMonitoring: true,
      securityGroup,
      role,
    });
    return launchTemplate;
  }

  newEcsTaskRole(): iam.Role {
    const ns = this.node.tryGetContext('ns') as string;

    const role = new iam.Role(this, `EcsTaskRole`, {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      roleName: `${ns}EcsTaskRole`,
    });
    // for EFS
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          'elasticfilesystem:ClientMount',
          'elasticfilesystem:ClientWrite',
          'elasticfilesystem:DescribeMountTargets',
        ],
        resources: ['*'],
      })
    );
    // for Secrets Manager
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: ['secretsmanager:GetSecretValue'],
        resources: ['*'],
        effect: iam.Effect.ALLOW,
      })
    );
    // for dynamodb
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          'dynamodb:DescribeTable',
          'dynamodb:PutItem',
          'dynamodb:GetItem',
          'dynamodb:UpdateItem',
          'dynamodb:Scan',
        ],
        resources: ['*'],
        effect: iam.Effect.ALLOW,
      })
    );
    // for cloudmap
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          'ec2:DescribeTags',
          'ecs:CreateCluster',
          'ecs:DeregisterContainerInstance',
          'ecs:DiscoverPollEndpoint',
          'ecs:Poll',
          'ecs:RegisterContainerInstance',
          'ecs:StartTelemetrySession',
          'ecs:UpdateContainerInstancesState',
          'ecs:Submit*',
          'ecr:GetAuthorizationToken',
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: ['*'],
        effect: iam.Effect.ALLOW,
      })
    );
    // for X-Ray and ADOT
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          'logs:PutLogEvents',
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:DescribeLogStreams',
          'logs:DescribeLogGroups',
          'xray:PutTraceSegments',
          'xray:PutTelemetryRecords',
          'xray:GetSamplingRules',
          'xray:GetSamplingTargets',
          'xray:GetSamplingStatisticSummaries',
          'ssm:GetParameters',
        ],
        resources: ['*'],
        effect: iam.Effect.ALLOW,
      })
    );

    return role;
  }

  newEcsTaskExecutionRole(): iam.Role {
    const ns = this.node.tryGetContext('ns') as string;

    const role = new iam.Role(this, `EcsTaskExecutionRole`, {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      roleName: `${ns}EcsTaskExecutionRole`,
    });
    // ECS Task Execution Role
    role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          's3:GetObject',
          'ecr:GetAuthorizationToken',
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetDownloadUrlForLayer',
          'ecr:BatchGetImage',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
          'ssm:GetParameters',
        ],
        resources: ['*'],
      })
    );
    return role;
  }

  newEcsTaskLogGroup(): logs.ILogGroup {
    const ns = this.node.tryGetContext('ns') as string;
    return new logs.LogGroup(this, `TaskLogGroup`, {
      logGroupName: `${ns}/ecs-task`,
      removalPolicy: RemovalPolicy.DESTROY,
    });
  }

  newEcsCluster(
    props: IProps,
    launchTemplate: ec2.ILaunchTemplate
  ): ecs.ICluster {
    const ns = this.node.tryGetContext('ns') as string;

    const cluster = new ecs.Cluster(this, `Cluster`, {
      clusterName: ns,
      vpc: props.vpc,
      defaultCloudMapNamespace: {
        name: ns.toLowerCase(),
        type: cloudmap.NamespaceType.DNS_PRIVATE,
        vpc: props.vpc,
        useForServiceConnect: true,
      },
      containerInsights: true,
    });

    const autoScalingGroup = new autoscaling.AutoScalingGroup(this, 'ASG', {
      vpc: props.vpc,
      minCapacity: 1,
      maxCapacity: 2,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      launchTemplate,
    });

    const capacityProvider = new ecs.AsgCapacityProvider(
      this,
      'AsgCapacityProvider',
      {
        autoScalingGroup,
        machineImageType: ecs.MachineImageType.AMAZON_LINUX_2,
      }
    );
    cluster.addAsgCapacityProvider(capacityProvider);

    return cluster;
  }

  newSecurityGroup(props: IProps): ec2.ISecurityGroup {
    const ns = this.node.tryGetContext('ns') as string;

    const securityGroup = new ec2.SecurityGroup(this, 'SecurityGroup', {
      securityGroupName: `${ns}EcsCluster`,
      vpc: props.vpc,
    });
    securityGroup.connections.allowInternally(
      ec2.Port.allTcp(),
      'Internal Service'
    );
    securityGroup.connections.allowFrom(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.allTcp()
    );

    return securityGroup;
  }

  newApplicationLoadBalancer(
    props: IProps,
    securityGroup: ec2.ISecurityGroup
  ): elbv2.IApplicationLoadBalancer {
    const ns = this.node.tryGetContext('ns') as string;

    const alb = new elbv2.ApplicationLoadBalancer(this, `ApplicationLB`, {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup,
    });

    new CfnOutput(this, 'LoadBalancerDNS', {
      exportName: `${ns}LoadBalancerDNS`,
      value: alb.loadBalancerDnsName,
    });

    return alb;
  }
}
