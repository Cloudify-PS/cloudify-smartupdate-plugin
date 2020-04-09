PREUPDATE_INTERFACE = 'cloudify.interfaces.preupdate'
UPDATE_INTERFACE = 'cloudify.interfaces.update'
POSTUPDATE_INTERFACE = 'cloudify.interfaces.postupdate'

PREUPDATE_OPERATIONS = [
    PREUPDATE_INTERFACE + '.stop',
    PREUPDATE_INTERFACE + '.delete'
]
UPDATE_OPERATION = UPDATE_INTERFACE + '.update'
POSTUPDATE_OPERATIONS = [
    POSTUPDATE_INTERFACE + '.create',
    POSTUPDATE_INTERFACE + '.configure',
    POSTUPDATE_INTERFACE + '.start'
]
