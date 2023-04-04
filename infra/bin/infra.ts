#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcStack } from '../lib/stacks/vpc-stack';
import { EcsClusterStack } from '../lib/stacks/ecs-cluster-stack';
import { EfsStack } from '../lib/stacks/efs-stack';
import { FrontServiceStack } from '../lib/stacks/services/front-service-stack';
import { ChatbotServiceStack } from '../lib/stacks/services/chatbot-service-stack';
import { Config } from '../config/loader';

const app = new cdk.App({
  context: {
    ns: Config.app.ns,
    stage: Config.app.stage,
  },
});

const vpcStack = new VpcStack(app, `${Config.app.ns}VpcStack`, {
  vpcId: Config.vpc.id,
  env: {
    account: Config.aws.account,
    region: Config.aws.region,
  },
});

const efsStack = new EfsStack(app, `${Config.app.ns}EfsStack`, {
  vpc: vpcStack.vpc,
  env: {
    account: Config.aws.account,
    region: Config.aws.region,
  },
});
efsStack.addDependency(vpcStack);

const ecsClusterStack = new EcsClusterStack(
  app,
  `${Config.app.ns}EcsClusterStack`,
  {
    vpc: vpcStack.vpc,
    env: {
      account: Config.aws.account,
      region: Config.aws.region,
    },
  }
);
ecsClusterStack.addDependency(vpcStack);

const frontServiceStack = new FrontServiceStack(
  app,
  `${Config.app.ns}FrontServiceStack`,
  {
    vpc: vpcStack.vpc,
    alb: ecsClusterStack.alb,
    cluster: ecsClusterStack.cluster,
    taskRole: ecsClusterStack.taskRole,
    taskLogGroup: ecsClusterStack.taskLogGroup,
    taskExecutionRole: ecsClusterStack.taskExecutionRole,
    taskSecurityGroup: ecsClusterStack.taskSecurityGroup,
    service: {
      port: Config.service.common.port,
      name: Config.service.front.name,
      repositoryName: Config.service.front.repositoryName,
      tag: Config.service.front.tag,
    },
    env: {
      account: Config.aws.account,
      region: Config.aws.region,
    },
  }
);
frontServiceStack.addDependency(ecsClusterStack);

const chatbotServiceStack = new ChatbotServiceStack(
  app,
  `${Config.app.ns}ChatbotServiceStack`,
  {
    vpc: vpcStack.vpc,
    fileSystem: efsStack.fileSystem,
    cluster: ecsClusterStack.cluster,
    taskRole: ecsClusterStack.taskRole,
    taskLogGroup: ecsClusterStack.taskLogGroup,
    taskExecutionRole: ecsClusterStack.taskExecutionRole,
    taskSecurityGroup: ecsClusterStack.taskSecurityGroup,
    service: {
      port: Config.service.common.port,
      name: Config.service.chatbot.name,
      repositoryName: Config.service.chatbot.repositoryName,
      tag: Config.service.chatbot.tag,
    },
    env: {
      account: Config.aws.account,
      region: Config.aws.region,
    },
  }
);
chatbotServiceStack.addDependency(efsStack);
chatbotServiceStack.addDependency(ecsClusterStack);

const tags = cdk.Tags.of(app);
tags.add('namespace', Config.app.ns);
tags.add('stage', Config.app.stage);

app.synth();
