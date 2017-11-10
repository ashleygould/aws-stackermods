"""
vpc
    cidrblock
    routetable
        pub
        priv
    internetgw
    az
        subnet
            pub
                subnet2rtassoc -> routetable.pub
                natgw
                natgweip -> natgw
                defaultroute -> internetgw
            priv
                subnet2rtassoc -> routetable.priv
                defaultroute -> az.subnet.pub.natgw

subnet:
    name: str
    type: (public|private)
    public-subnet: (subnet.name|None)
    routetable: str
    availabilty-zones: list

azsubnet:
    name: (str) subnet.name + az-index
    subnet: subnet
    az: str
    az-index: int
    cidrblock: (str) get(subnet.type,vpc-cidr,az-index)
    routetable-assoc: subnet.routetable
    route-default: (str) get(subnet.type, subnet.public-subnet,az-index)
    natgw:
    natgweip:
    natgw-assoc:
"""




from troposphere import (
    Ref,
    Output,
    Join,
    #FindInMap,
    Select,
    GetAZs,
    #Tags,
    GetAtt
)
from troposphere import ec2
#from troposphere.route53 import HostedZone, HostedZoneVPCs
from stacker.blueprints.base import Blueprint
#from stacker.blueprints.variables.types import CFNString



# Default public/private subnet layout
DEFAULT_SUBNETS = {
        'Public': dict(net_type='public', public_subnet=None),
        'Private': dict(net_type='private', public_subnet='Public')}

# These get used as the cfn logical resource names
GATEWAY = 'InternetGateway'
GW_ATTACH = 'GatewayAttach'
VPC_NAME = 'VPC'
VPC_ID = Ref(VPC_NAME)


class VPC(Blueprint):
    """
    inputs:
        region (str:allowed-cfntype.region)
        vcp-cidr (str:allowed-regex)
        az-count (int)
        use-default-subnets (bool)
        subnets:
          - name (str)
            net_type (str:allowed-values)
            public_subnet (str)
    """
    VARIABLES = {
        'VpcCIDR': {
            'type': str,
            'description': 'vpc cidr block. must be class b (i.e. /16).',
            'default': '10.10.0.0/16',
        },
        'AZCount': {
            'type': int,
            'default': 2,
        },
        'UseDefaultSubnets': {
            'type': bool,
            'default': True,
        },
        'CustomSubnets': {
            'type': dict,
            'default': dict(),
        },
    }


    def validate_custom_subnets(self):
        # compose subnet definitions dictionary
        variables = self.get_variables()
        subnets = dict()
        if variables['UseDefaultSubnets']:
            subnets.update(DEFAULT_SUBNETS)
        subnets.update(variables['CustomSubnets'])
        # validate custom subnet definitions
        public_subnets = [subnet for subnet, attributes in subnets.items()
                if 'net_type' in attributes and attributes['net_type'] == 'public']
        for subnet, attributes in variables['CustomSubnets'].items():
            if not 'net_type' in attributes:
                raise ValueError("User provided subnets must have 'net_type' field")
            if attributes['net_type'] not in ['public', 'private']:
                raise ValueError("Value of 'net_type' field in user provided subnets "
                                 "must be one of ['public', 'private']")
            if attributes['net_type'] == 'private':
                if not 'public_subnet' in attributes:
                    raise ValueError("User provided subnets must have 'public_subnet' "
                                     "field if 'net_type' is 'private'")
                if attributes['public_subnet'] not in public_subnets:
                    raise ValueError("'%s' is not a valid 'public_subnet' name in user "
                                     "provided subnet '%s'"
                                     % (attributes['public_subnet'], subnet))
        return subnets


    def availability_zones(self):
        variables = self.get_variables()
        zones = []
        for i in range(variables['AZCount']):
            az = Select(i, GetAZs(''))
            zones.append(az)
        return zones


    def subnet_cidr(self, vpc_cidr, subnet_index, az_index):
        cidr_parts = vpc_cidr.split('.')
        cidr_parts[2] = str(int(cidr_parts[2]) + (subnet_index * 10) + az_index)
        return '.'.join(cidr_parts).replace('/16','/24')


    def create_vpc(self):
        t = self.template
        variables = self.get_variables()
        t.add_resource(ec2.VPC(
            'VPC',
            CidrBlock=variables['VpcCIDR'],
            EnableDnsHostnames=True))
        t.add_output(Output("VpcId", Value=VPC_ID))


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
                        CidrBlock=self.subnet_cidr(variables['VpcCIDR'], subnet_count, i),
                        #Tags=Tags(type=net_type),
                        #DependsOn=GW_ATTACH,
                        VpcId=VPC_ID))
            subnet_count += 1


    def create_nat_gateways(self, subnets, zones):
        # Nat gateways in public subnets, one per AZ
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'public':
                subnets[name]['nat_gateways'] = list()
                for i in range(len(zones)):
                    nat_gateway= '%sNatGateway%d' % (name, i)
                    nat_gateway_eip = '%sNatGatewayEIP%d' % (name, i)
                    subnets[name]['nat_gateways'].append(nat_gateway)
                    t.add_resource(ec2.EIP(
                            nat_gateway_eip,
                            #DependsOn=GW_ATTACH,
                            Domain='vpc'))
                    t.add_resource(ec2.NatGateway(
                            nat_gateway,
                            SubnetId=Ref(subnets[name]['az_subnets'][i]),
                            AllocationId=GetAtt(nat_gateway_eip, 'AllocationId')))


    def create_route_tables(self, subnets):
        # one route table for each subnet
        t = self.template
        for name in subnets.keys():
            route_table_name = '%sRouteTable' % name
            subnets[name]['route_table'] = route_table_name
            t.add_resource(ec2.RouteTable(
                    #Tags=[ec2.Tag('type', net_type)],
                    route_table_name,
                    VpcId=VPC_ID,))


    def create_route_table_associations(self, subnets, zones):
        # Accociate each az subnet to a route table
        t = self.template
        for name in subnets.keys():
            for i in range(len(zones)):
                t.add_resource(ec2.SubnetRouteTableAssociation(
                        '%sRouteTableAssociation%d' % (name, i),
                        SubnetId=Ref(subnets[name]['az_subnets'][i]),
                        RouteTableId=Ref(subnets[name]['route_table'])))


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
        # Default routes for private subnets through nat gateways
        t = self.template
        for name in subnets.keys():
            if subnets[name]['net_type'] == 'private':
                for i in range(len(zones)):
                    public_subnet = subnets[name]['public_subnet']
                    nat_gateway = subnets[public_subnet]['nat_gateways'][i]
                    t.add_resource(ec2.Route(
                            '%sSubnetDefaultRoute%d' % (name, i),
                            RouteTableId=Ref(subnets[name]['route_table']),
                            DestinationCidrBlock='0.0.0.0/0',
                            NatGatewayId=Ref(nat_gateway)))


    def create_template(self):
        subnets = self.validate_custom_subnets()
        zones = self.availability_zones()
        self.create_vpc()
        self.create_internet_gateway()
        self.create_subnets_in_availability_zones(subnets, zones)
        self.create_nat_gateways(subnets, zones)
        self.create_route_tables(subnets)
        self.create_route_table_associations(subnets, zones)
        self.create_default_routes_for_public_subnets(subnets)
        self.create_default_routes_for_private_subnets(subnets, zones)
        ## Debugging
        #variables = self.get_variables()
        #print('variables: %s' % variables)
        #print('zones: %s' % zones)
        #print('subnets: %s' % subnets)


        ## Outputs
        #for net_type in net_types:
        #    t.add_output(Output(
        #            '%sSubnets' % net_type.capitalize(),
        #            Value=Join(',', [Ref(sn) for sn in subnets[net_type]])))
        #    for i, sn in enumerate(subnets[net_type]):
        #        t.add_output(Output(sn, Value=Ref(sn)))
        #t.add_output(Output(
        #        'AvailabilityZones',
        #        Value=Join(',', zones)))
        #for i, az in enumerate(zones):
        #    t.add_output(Output(
        #            'AvailabilityZone0%d' % (i +1),
        #            Value=az))
        
