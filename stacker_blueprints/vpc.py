from troposphere import (
    #Ref,
    Output,
    #Join,
    #FindInMap,
    #Select,
    #GetAZs,
    #Tags,
    #GetAtt
)
from troposphere import ec2
#from troposphere.route53 import HostedZone, HostedZoneVPCs
from stacker.blueprints.base import Blueprint
#from stacker.blueprints.variables.types import CFNString


class VPC(Blueprint):
    VARIABLES = {
        'VpcCIDR': {
            'type': str,
            'description': 'vpc cidr block',
            'default': '10.10.0.0/16',
        }

    }


    def create_vpc(self):
        t = self.template
        variables = self.get_variables()
        print(variables)
        t.add_resource(ec2.VPC(
            'VPC',
            CidrBlock=variables['VpcCIDR'],
            #EnableDnsSupport=True,
            EnableDnsHostnames=True))

        # Just about everything needs this, so storing it on the object
        #t.add_output(Output("VpcId", Value=VPC_ID))

    def create_template(self):
        self.create_vpc()

