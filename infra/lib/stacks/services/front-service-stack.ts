import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IServiceProps } from '../../interfaces/types';
import { FrontService } from '../../constructs/front-service';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ssm from 'aws-cdk-lib/aws-ssm';

interface IProps extends IServiceProps {
  vpc: ec2.IVpc;
  alb: elbv2.IApplicationLoadBalancer;
}

export class FrontServiceStack extends Stack {
  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    const taskEnvs = {
      CHAT_ENDPOINT: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvChatEndpoint', {
          stringValue: `http://chatbot.chatbotdemodev:8080/v1/chat/`,
        })
      ),
      AWS_XRAY_DAEMON_ADDRESS: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvXrayDaemon', {
          stringValue: `xray-daemon.chatbotdemodev:2000`,
        })
      ),
    };

    const frontService = new FrontService(this, 'FrontService', {
      ...props,
      taskEnvs,
    });
    this.registerServiceToLoadBalancer(frontService.ecsService, props);
  }

  registerServiceToLoadBalancer(ecsService: ecs.Ec2Service, props: IProps) {
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'ListenerRule', {
      protocol: elbv2.ApplicationProtocol.HTTP,
      port: props.service.port,
      vpc: props.vpc,
      targets: [ecsService],
      healthCheck: {
        enabled: true,
        path: '/healthz/',
        healthyHttpCodes: '200-299',
      },
    });

    new elbv2.ApplicationListener(this, 'Listener', {
      loadBalancer: props.alb,
      protocol: elbv2.ApplicationProtocol.HTTP,
      port: 8000,
      defaultTargetGroups: [targetGroup],
    });
  }
}
