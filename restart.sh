#!/bin/bash

sudo docker stop violas-monitor-backend
sudo docker rm violas-monitor-backend
sudo docker image rm violas-monitor-backend
sudo docker image build -t violas-monitor-backend .
sudo docker run --name=violas-monitor-backend --network=host -d violas-monitor-backend