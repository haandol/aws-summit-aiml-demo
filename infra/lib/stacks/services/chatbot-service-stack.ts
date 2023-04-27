import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IChatbotServiceProps } from '../../interfaces/types';
import { ChatbotService } from '../../constructs/chatbot-service';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ssm from 'aws-cdk-lib/aws-ssm';

interface IProps extends IChatbotServiceProps {
  vpc: ec2.IVpc;
}

export class ChatbotServiceStack extends Stack {
  constructor(scope: Construct, id: string, props: IProps) {
    super(scope, id, props);

    const taskEnvs = {
      NVIDIA_VISIBLE_DEVICES: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvNvidiaVisibleDevices', {
          stringValue: 'all',
        })
      ),
      OTEL_SERVICE_NAME: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvOtelService', {
          stringValue: `chatbot`,
        })
      ),
      OTEL_EXPORTER_OTLP_ENDPOINT: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvOtelDaemon', {
          stringValue: `http://otel.chatbotdemodev:4317`,
        })
      ),
      LOAD_IN_8BIT: ecs.Secret.fromSsmParameter(
        new ssm.StringParameter(this, 'EnvLoadIn8bit', {
          stringValue: `true`,
        })
      ),
    };

    new ChatbotService(this, 'ChatbotService', {
      ...props,
      taskEnvs,
    });
  }
}
