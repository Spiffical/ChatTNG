#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ChatTNGStack } from '../lib/chattng-stack';

const app = new cdk.App();
new ChatTNGStack(app, 'ChatTNGStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
}); 