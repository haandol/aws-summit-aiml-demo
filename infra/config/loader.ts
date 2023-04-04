import * as fs from 'fs';
import * as path from 'path';
import * as joi from 'joi';
import * as toml from 'toml';
import { VpcValidator } from './validators';

type IService = {
  name: string;
  repositoryName: string;
};

export interface IConfig {
  app: {
    ns: string;
    stage: string;
  };
  aws: {
    account: string;
    region: string;
  };
  vpc: {
    id: string;
  };
  service: {
    common: {
      port: number;
      tag: string;
    };
    front: IService;
    chatbot: IService;
  };
}

const cfg = toml.parse(
  fs.readFileSync(path.resolve(__dirname, '..', '.toml'), 'utf-8')
);
console.log('loaded config', cfg);

const schema = joi
  .object({
    app: joi.object({
      ns: joi.string().required(),
      stage: joi.string().required(),
    }),
    aws: joi.object({
      account: joi.number().required(),
      region: joi.string().required(),
    }),
    vpc: joi.object({
      id: joi.string().custom(VpcValidator).required(),
    }),
    service: joi.object({
      common: joi.object({
        port: joi.number().required(),
        tag: joi.string().required(),
      }),
      front: joi.object({
        name: joi.string().required(),
        repositoryName: joi.string().required(),
      }),
      chatbot: joi.object({
        name: joi.string().required(),
        repositoryName: joi.string().required(),
      }),
    }),
  })
  .unknown();

const { error } = schema.validate(cfg);

if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

export const Config: IConfig = {
  ...cfg,
  app: {
    ...cfg.app,
    ns: `${cfg.app.ns}${cfg.app.stage}`,
  },
};
