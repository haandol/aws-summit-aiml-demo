import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IServiceProps } from '../../interfaces/types';
import { FrontendService } from '../../constructs/frontend-service';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';

interface IProps extends IServiceProps {
  vpc: ec2.IVpc;
  alb: elbv2.IApplicationLoadBalancer;
}

export class FrontendServiceStack extends Stack {
  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    const feService = new FrontendService(this, 'FrontendService', {
      ...props,
    });
    this.registerServiceToLoadBalancer(feService.ecsService, props);
  }

  registerServiceToLoadBalancer(ecsService: ecs.Ec2Service, props: IProps) {
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'ListenerRule', {
      protocol: elbv2.ApplicationProtocol.HTTP,
      port: props.service.port,
      vpc: props.vpc,
      targets: [ecsService],
      healthCheck: {
        path: '/healthz',
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
