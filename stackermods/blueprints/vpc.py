"""
A stacker blueprint module to generate a VPC and subnets.

AWS resources created:
    VPC with attached InternetGateway
    Public and private subnets spanning AvailabilityZones per specification
    NatGatways in Public subnets
    RouteTables and default routes for all subnets.

By default we build a Public and a Private subnet in each of 2 AvailabilityZones.
To add custom subnets or span additional AZs, specify alternative variable values
in your stacker config file.  See a sample in './conf/vpc.conf.yml'.
"""


from stacker.blueprints.base import Blueprint
from troposphere import (
    Ref,
    Output,
    Join,
    Select,
    GetAZs,
    Tags,
    GetAtt,
    ec2
)


# Default public/private subnet layout
DEFAULT_SUBNETS = {
        'Public': dict(net_type='public', gateway_subnet=None, priority=0),
        'Private': dict(net_type='private', gateway_subnet='Public', priority=1)}

# Some global cfn logical resource names
GATEWAY = 'InternetGateway'
GW_ATTACH = 'InternetGatewayAttachment'
VPC_NAME = 'VPC'
VPC_ID = Ref(VPC_NAME)



def help():
    bp = VPC('VPC', None)
    print(__doc__)
    print('\nConfig variables for %s blueprint:\n' % bp.name)
    vars = getattr(bp, "VARIABLES", {})
    for var, attr in sorted(vars.items()):
        default = attr.get('default', '')
        desc = attr.get('description', '')
        print("%s\n  %s\n  Default: %s\n" % (var, desc, default))


def validate_cidrblock(cidrblock):
    import re
    cidr_re = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')
    if cidr_re.match(cidrblock):
        ip, mask = cidrblock.split('/')
        for q in ip.split('.'):
            if int(q) > 255:
                raise ValueError("'%s' not a valid cidr block" % cidrblock)
        if int(mask) != 16:
            raise ValueError("'VpcCIDR' must define a class 'B' network")
        return cidrblock
    raise ValueError("'%s' not a valid cidr block" % cidrblock)


def validate_custom_subnets(custom_subnets):
    for subnet, attributes in custom_subnets.items():
        if not 'net_type' in attributes:
            raise ValueError("User provided subnets must have 'net_type' field")
        if attributes['net_type'] not in ['public', 'private']:
            raise ValueError("Value of 'net_type' field in user provided subnets "
                             "must be one of ['public', 'private']")
        if attributes['net_type'] == 'private':
            if not 'gateway_subnet' in attributes:
                raise ValueError("User provided subnets must have 'gateway_subnet' "
                                 "field if 'net_type' is 'private'")
        if not 'priority' in attributes:
            raise ValueError("User provided subnets must have 'priority' field")
        if not isinstance(attributes['priority'], int) or attributes['priority'] >= 25:
            raise ValueError("Value of 'priority' field in user provided subnets "
                             "must be an integer less than 25")
    return custom_subnets


def validate_az_count(count):
    if count >= 10:
        raise ValueError("Value of 'AZCount' must be an integer less than 10")
    return count




class VPC(Blueprint):

    VARIABLES = {
        'VpcCIDR': {
            'type': str,
            'default': '10.10.0.0/16',
            'validator': validate_cidrblock,
            'description': (
"""Cidr block for the VPC.  Must define a class B network (i.e. '/16')."""),
        },
        'AZCount': {
            'type': int,
            'default': 2,
            'validator': validate_az_count,
            'description': (
"""Number of Availability Zones to use.  Must be an integer less than 10."""),
        },
        'UseDefaultSubnets': {
            'type': bool,
            'default': True,
            'description': (
"""Whether or not to create the default 'Public' and 'Private' subnets."""),
        },
        'CustomSubnets': {
            'type': dict,
            'default': dict(),
            'validator': validate_custom_subnets,
            'description': (
"""Dictionary of custom subnets to create in addition to or instead of the
  default 'Public' and 'Private' subnets.  Each custom subnet is a dictionary
  with the following keys:
    'net_type' - either 'public' or 'private',
    'priority' - integer used to determine the subnet cidr block.  Must
                 be unique among all subnets.
    'gateway_subnet' - the public subnet to use as a default route.
                       Required for subnets of net_type 'private'.
  Example (yaml):                       
    DB:
      net_type: private
      gateway_subnet: Public
      priority: 2
    App:
      net_type: private
      gateway_subnet: Public
      priority: 3 """),
        },
        'Tags': {
            'type': dict,
            'default': dict(),
            'description': (
"""Dictionary of tags to apply to stack resources (e.g. {tagname: value})"""),
        },
    }


    def munge_subnets(self):
        # compose subnet definitions dictionary
        variables = self.get_variables()
        subnets = dict()
        if variables['UseDefaultSubnets']:
            subnets.update(DEFAULT_SUBNETS)
        subnets.update(variables['CustomSubnets'])
        return subnets


    def availability_zones(self):
        t = self.template
        variables = self.get_variables()
        zones = []
        for i in range(variables['AZCount']):
            az = Select(i, GetAZs(''))
            zones.append(az)
        t.add_output(Output('AvailabilityZones', Value=Join(",", zones)))
        return zones


    def subnet_cidr(self, subnets, name, az_index):
        variables = self.get_variables()
        other_priorities = [attr['priority'] for subnet, attr in subnets.items()
                if subnet != name]
        if subnets[name]['priority'] in other_priorities:
            raise ValueError("subnet priority '%d' is not unique for subnet '%s'" %
                    (subnets[name]['priority'], name))
        cidr_parts = variables['VpcCIDR'].split('.')
        quod = (subnets[name]['priority'] * 10) + az_index
        cidr_parts[2] = str(quod)
        return '.'.join(cidr_parts).replace('/16','/24')


    def create_vpc(self):
        t = self.template
        variables = self.get_variables()
        t.add_resource(ec2.VPC(
                VPC_NAME,
                CidrBlock=variables['VpcCIDR'],
                EnableDnsHostnames=True,
                Tags=Tags(variables['Tags']),
                ))
        t.add_output(Output("VpcId", Value=VPC_ID))
        t.add_output(Output("CIDR", Value=variables['VpcCIDR']))


    def create_internet_gateway(self):
        t = self.template
        t.add_resource(ec2.InternetGateway(GATEWAY))
        t.add_resource(ec2.VPCGatewayAttachment(
                GW_ATTACH,
                InternetGatewayId=Ref(GATEWAY),
                VpcId=VPC_ID))


    def create_subnets_in_availability_zones(self, subnets, zones):
        variables = self.get_variables()
        t = self.template
        subnet_count = 0
        for name in subnets.keys():
            subnets[name]['az_subnets'] = list()
            for i in range(len(zones)):
                subnet_name = '%sSubnet%d' % (name, i)
                subnets[name]['az_subnets'].append(subnet_name)
                t.add_resource(ec2.Subnet(
                        subnet_name,
                        AvailabilityZone=zones[i],
                        CidrBlock=self.subnet_cidr(subnets, name, i),
                        Tags=Tags(net_type=subnets[name]['net_type']) + Tags(variables['Tags']),
                        VpcId=VPC_ID))
        # Outputs
        for name in subnets:
            t.add_output(Output(
                    '%sSubnets' % name,
                    Value=Join(',', [Ref(sn) for sn in subnets[name]['az_subnets']])))


    def create_nat_gateways(self, subnets, zones):
        # Nat gateways in public subnets, one per AZ
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'public':
                if name == 'Public':
                    prefix = ''
                else:
                    prefix = name
                subnets[name]['nat_gateways'] = list()
                for i in range(len(zones)):
                    nat_gateway= '%sNatGateway%d' % (prefix, i)
                    nat_gateway_eip = '%sNatGatewayEIP%d' % (prefix, i)
                    subnets[name]['nat_gateways'].append(nat_gateway)
                    t.add_resource(ec2.EIP(
                            nat_gateway_eip,
                            Domain='vpc'))
                    t.add_resource(ec2.NatGateway(
                            nat_gateway,
                            SubnetId=Ref(subnets[name]['az_subnets'][i]),
                            AllocationId=GetAtt(nat_gateway_eip, 'AllocationId')))


    def create_public_route_tables(self, subnets):
        # one route table for each public subnet
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'public':
                route_table_name = '%sRouteTable' % name
                subnets[name]['route_table'] = route_table_name
                t.add_resource(ec2.RouteTable(
                        #Tags=[ec2.Tag('type', net_type)],
                        route_table_name,
                        VpcId=VPC_ID,))


    def create_private_route_tables(self, subnets, zones):
        # one route table for each az for private subnets
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'private':
                subnets[name]['route_table'] = list()
                for i in range(len(zones)):
                    route_table_name = '%sRouteTable%d' % (name, i)
                    subnets[name]['route_table'].append(route_table_name)
                    t.add_resource(ec2.RouteTable(
                            #Tags=[ec2.Tag('type', net_type)],
                            route_table_name,
                            VpcId=VPC_ID,))


    def create_route_table_associations(self, subnets, zones):
        # Accociate each az subnet to a route table
        t = self.template
        for name in subnets.keys():
            for i in range(len(zones)):
                if subnets[name]['net_type'] == 'public':
                    route_table_name = subnets[name]['route_table']
                else:
                    route_table_name = subnets[name]['route_table'][i]
                t.add_resource(ec2.SubnetRouteTableAssociation(
                        '%sRouteTableAssociation%d' % (name, i),
                        SubnetId=Ref(subnets[name]['az_subnets'][i]),
                        RouteTableId=Ref(route_table_name)))


    def create_default_routes_for_public_subnets(self, subnets):
        # Add route through Internet Gateway to route tables for public subnets
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'public':
                t.add_resource(ec2.Route(
                        '%sSubnetDefaultRoute' % name,
                        RouteTableId=Ref(subnets[name]['route_table']),
                        DestinationCidrBlock='0.0.0.0/0',
                        GatewayId=Ref(GATEWAY)))


    def create_default_routes_for_private_subnets(self, subnets, zones):
        # Default routes for private subnets through nat gateways in each az.
        # Use the nat gateways defined in the 'gateway_subnet' for eash subnet.
        t = self.template
        public_subnets = [subnet for subnet, attributes in subnets.items()
                if attributes['net_type'] == 'public']
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'private':
                for i in range(len(zones)):
                    gateway_subnet = subnets[name]['gateway_subnet']
                    nat_gateway = subnets[gateway_subnet]['nat_gateways'][i]
                    if gateway_subnet not in public_subnets:
                        raise ValueError("'%s' is not a valid 'gateway_subnet' name in "
                                "subnet '%s'" % (gateway_subnet, subnet))
                    t.add_resource(ec2.Route(
                            '%sSubnetDefaultRoute%d' % (name, i),
                            RouteTableId=Ref(subnets[name]['route_table'][i]),
                            DestinationCidrBlock='0.0.0.0/0',
                            NatGatewayId=Ref(nat_gateway)))


    def create_template(self):
        subnets = self.munge_subnets()
        zones = self.availability_zones()
        self.create_vpc()
        self.create_internet_gateway()
        self.create_subnets_in_availability_zones(subnets, zones)
        self.create_nat_gateways(subnets, zones)
        self.create_public_route_tables(subnets)
        self.create_private_route_tables(subnets, zones)
        self.create_route_table_associations(subnets, zones)
        self.create_default_routes_for_public_subnets(subnets)
        self.create_default_routes_for_private_subnets(subnets, zones)
        ## Debugging
        #variables = self.get_variables()
        #print('variables: %s' % variables)
        #print('zones: %s' % zones)
        #print('subnets: %s' % subnets)
