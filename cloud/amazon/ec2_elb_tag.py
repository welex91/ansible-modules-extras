#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: ec2_elb_tag
short_description: Tag Amazon ELB.
description:
  - Add tags for an EC2 Elastic Load Balancers in AWS.
  - Will be marked changed when called only if state is changed.
version_added: "2.1"
author: "Sumit Roy (@welex91)"
options:
  name:
    description:
      - ELB name to tag.
    required: true
    default: null
  state:
    description:
      - Whether the tags should be present or absent on the resource. Use list to interrogate the tags of an instance.
    required: false
    default: present
    choices: ['present', 'absent', 'list']
  tags:
    description:
      - a hash/dictionary of tags to add to the resource; '{"key":"value"}' and '{"key":"value","key":"value"}'
    required: false
    default: null

extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.
# Tag 
tasks:
- name: tag an ELB
  ec2_elb_tag:
    region: us-east-1
    name: frontend-prod-elb
    tags:
      Tier: "Frontend"
      Stack: "Production"
    state: present
'''

try:
    import boto
    import boto.ec2.elb
    import boto.ec2.elb.attributes
    from boto.ec2.elb.healthcheck import HealthCheck
    from boto.ec2.elb.loadbalancer import LoadBalancer
    from boto.ec2.tag import Tag
    from boto.regioninfo import RegionInfo
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            name = {'required': True},
            tags = dict(),
            state = dict(default='present', choices=['present', 'absent', 'list'])
        )
    )

    module = AnsibleModule(argument_spec=argument_spec)

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')

    name = module.params['name']
    tags = module.params['tags']
    state = module.params['state']
    
    region, ec2_url, aws_connect_params = get_aws_connection_info(module)

    if region:
        try:
            connection = connect_to_aws(boto.ec2.elb, region, **aws_connect_params)
        except (boto.exception.NoAuthHandlerFound, StandardError), e:
            module.fail_json(msg=str(e))
    else:
        module.fail_json(msg="Region must be specified as a parameter, in EC2_REGION or AWS_REGION environment variables or in boto configuration file")

    params = {'LoadBalancerNames.member.1': name}

    # get the current list of tags from the ELB
    current_tags = connection.get_list('DescribeTags', params,
                                       [('member', Tag)])
    tagdict = {tag.Key : tag.Value for tag in current_tags
               if hasattr(tag, 'Key')}

    if state == 'list' :
        module.exit_json(changed=False, tags=tagdict)
    elif state == 'present':
        if not tags:
            module.fail_json(msg="tags argument is required when state is present")
        dictact = dict(set(tags.items()) - set(tagdict.items()))
        if not dictact:
            module.exit_json(msg="Tags already exist in %s."
                             % name, changed=False)
        else:
            for i, key in enumerate(dictact):
                params['Tags.member.%d.Key' % (i + 1)] = key
                params['Tags.member.%d.Value' % (i + 1)] = dictact[key]

        connection.make_request('AddTags', params)
        module.exit_json(msg="Tags %s created for ELB %s." % (dictact,name), changed=True)
    elif state == 'absent':
        if not tags:
            module.fail_json(msg="tags argument is required when state is absent")
        dictact = dict(set(tags.items()) & set(tagdict.items()))
        if not dictact:
            module.exit_json(msg="Nothing to remove here. Move along.", changed=False)
        else:
            for i, key in enumerate(dictact):
                params['Tags.member.%d.Key' % (i + 1)] = key
        connection.make_request('RemoveTags', params)
        module.exit_json(msg="Tags %s removed for ELB %s." % (dictact,name), changed=True)


        
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
