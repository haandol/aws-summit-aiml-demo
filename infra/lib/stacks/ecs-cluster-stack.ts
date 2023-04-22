import { Stack, StackProps, RemovalPolicy } from 'aws-cdk-lib';
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

    const cluster = this.newEcsCluster(props);
    this.cluster = cluster;

    const role = new iam.Role(this, 'LaunchTemplateRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonEC2RoleforSSM'
        ),
      ],
    });
    const gpuLaunchTemplate = this.newGpuLaunchTemplate(
      role,
      this.taskSecurityGroup
    );
    const cpuLaunchTemplate = this.newCpuLaunchTemplate(
      role,
      this.taskSecurityGroup
    );
    this.updateAutoScalingGroup(cluster, gpuLaunchTemplate, cpuLaunchTemplate);

    this.alb = this.newApplicationLoadBalancer(props, this.taskSecurityGroup);
  }

  newGpuLaunchTemplate(
    role: iam.IRole,
    securityGroup: ec2.ISecurityGroup
  ): ec2.LaunchTemplate {
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config',
      'echo ECS_NVIDIA_RUNTIME=nvidia >> /etc/ecs/ecs.config'
    );
    const launchTemplate = new ec2.LaunchTemplate(this, 'GpuLaunchTemplate', {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.G4DN,
        ec2.InstanceSize.XLARGE2
      ),
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(512, {
            volumeType: ec2.EbsDeviceVolumeType.GP2,
            encrypted: true,
          }),
        },
      ],
      machineImage: ec2.MachineImage.lookup({
        name: 'amzn2-ami-ecs-gpu-hvm-2.0.20230321-x86_64-ebs',
      }),
      requireImdsv2: true,
      detailedMonitoring: true,
      userData,
      securityGroup,
      role,
    });
    return launchTemplate;
  }

  newCpuLaunchTemplate(
    role: iam.IRole,
    securityGroup: ec2.ISecurityGroup
  ): ec2.LaunchTemplate {
    const launchTemplate = new ec2.LaunchTemplate(this, 'CpuLaunchTemplate', {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.M5,
        ec2.InstanceSize.XLARGE
      ),
      blockDevices: [
        {
          deviceName: '/dev/xvda',
          volume: ec2.BlockDeviceVolume.ebs(128, {
            volumeType: ec2.EbsDeviceVolumeType.GP2,
            encrypted: true,
          }),
        },
      ],
      machineImage: ecs.EcsOptimizedImage.amazonLinux2(),
      userData: ec2.UserData.forLinux(),
      requireImdsv2: true,
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

  newEcsTaskLogGroup(): logs.LogGroup {
    const ns = this.node.tryGetContext('ns') as string;
    return new logs.LogGroup(this, `TaskLogGroup`, {
      logGroupName: `${ns}/ecs-task`,
      removalPolicy: RemovalPolicy.DESTROY,
    });
  }

  newEcsCluster(props: IProps): ecs.Cluster {
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

    return cluster;
  }

  updateAutoScalingGroup(
    cluster: ecs.Cluster,
    gpuLaunchTemplate: ec2.ILaunchTemplate,
    cpuLaunchTemplate: ec2.ILaunchTemplate
  ) {
    const gpuAsg = new autoscaling.AutoScalingGroup(this, 'GpuAsg', {
      vpc: cluster.vpc,
      minCapacity: 1,
      desiredCapacity: 2,
      maxCapacity: 3,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      launchTemplate: gpuLaunchTemplate,
    });
    cluster.addAsgCapacityProvider(
      new ecs.AsgCapacityProvider(this, 'GpuAsgCapacityProvider', {
        autoScalingGroup: gpuAsg,
      })
    );

    const cpuAsg = new autoscaling.AutoScalingGroup(this, 'CpuAsg', {
      vpc: cluster.vpc,
      minCapacity: 1,
      desiredCapacity: 2,
      maxCapacity: 3,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      launchTemplate: cpuLaunchTemplate,
    });
    cluster.addAsgCapacityProvider(
      new ecs.AsgCapacityProvider(this, 'CpuAsgCapacityProvider', {
        autoScalingGroup: cpuAsg,
      })
    );
  }

  newSecurityGroup(props: IProps): ec2.SecurityGroup {
    const ns = this.node.tryGetContext('ns') as string;

    const securityGroup = new ec2.SecurityGroup(this, 'SecurityGroup', {
      securityGroupName: `${ns}EcsCluster`,
      vpc: props.vpc,
    });
    securityGroup.connections.allowInternally(
      ec2.Port.allTraffic(),
      'Internal Service'
    );
    securityGroup.connections.allowFrom(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.allTraffic()
    );

    return securityGroup;
  }

  newApplicationLoadBalancer(
    props: IProps,
    securityGroup: ec2.ISecurityGroup
  ): elbv2.ApplicationLoadBalancer {
    const alb = new elbv2.ApplicationLoadBalancer(this, `ApplicationLB`, {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup,
    });
    alb.connections.allowInternally(ec2.Port.allTcp(), 'Internal Service');
    alb.connections.allowFrom(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.allTcp(),
      'VPC Internal'
    );
    return alb;
  }
}
