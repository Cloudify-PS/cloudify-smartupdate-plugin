#!/usr/bin/env bash

cfy blueprint upload -b basic v3_service_component/basic.yaml
cfy blueprint upload -b basic_update v3_service_component/basic_update.yaml
cfy blueprint upload -b main v3_service_component/main.yaml
cfy blueprint upload -b main_update v3_service_component/main_update.yaml

