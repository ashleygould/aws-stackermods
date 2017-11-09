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

one vpc
one routetable per subnet def

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


# these get used as the cfn logical resource names
GATEWAY = 'InternetGateway'
GW_ATTACH = 'GatewayAttach'
VPC_NAME = 'VPC'
VPC_ID = Ref(VPC_NAME)
DEFAULT_SUBNETS = [
        dict(
            name='Public',
            net_type='public',
            public_subnet=None),
        dict(
            name='Private',
            net_type='private',
            public_subnet='Public'),
        ]


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
            'type': list,
            'default': [],
        },
    }

    def subnet_cidr(self, vpc_cidr, net_type, az_index):
        if net_type == 'public':
            subnet_qoud = '1' + str(az_index)
        elif net_type == 'private':
            subnet_qoud = '10' + str(az_index)
        cidr_parts = vpc_cidr.split('.')
        cidr_parts[2] = subnet_qoud
        return '.'.join(cidr_parts).replace('/16','/24')

    def create_vpc(self):
        t = self.template
        variables = self.get_variables()
        t.add_resource(ec2.VPC(
            'VPC',
            CidrBlock=variables['VpcCIDR'],
            #EnableDnsSupport=True,
            EnableDnsHostnames=True))

        # Just about everything needs this, so storing it on the object
        t.add_output(Output("VpcId", Value=VPC_ID))

    def create_gateway(self):
        t = self.template
        t.add_resource(ec2.InternetGateway(GATEWAY))
        t.add_resource(
            ec2.VPCGatewayAttachment(
                GW_ATTACH,
                VpcId=VPC_ID,
                InternetGatewayId=Ref(GATEWAY)
            )
        )

    def create_network(self):
        t = self.template
        variables = self.get_variables()
        self.create_gateway()
        subnets = {'public': [], 'private': []}
        net_types = subnets.keys()
        zones = []

        for net_type in net_types:
            name_prefix = net_type.capitalize()

            # one route table for each of pub an priv
            route_table_name = '%sRouteTable' % name_prefix
            t.add_resource(
                ec2.RouteTable(
                    route_table_name,
                    VpcId=VPC_ID,
                    #Tags=[ec2.Tag('type', net_type)]
                )
            )

            # Internet Gateway
            if net_type == 'public':
                t.add_resource(
                    ec2.Route(
                        'DefaultPublicRoute',
                        #RouteTableId=Ref(route_table_name),
                        RouteTableId=Ref('PublicRouteTable'),
                        DestinationCidrBlock='0.0.0.0/0',
                        GatewayId=Ref(GATEWAY)
                    )
                )

            # Public and private subnets for each Availability zone
            for i in range(variables['AZCount']):
                az = Select(i, GetAZs(''))
                zones.append(az)
                name_suffix = '0' + str(i + 1)
                subnet_name = '%sSubnet%s' % (name_prefix, name_suffix)
                subnets[net_type].append(subnet_name)
                t.add_resource(
                    ec2.Subnet(
                        subnet_name,
                        AvailabilityZone=az,
                        VpcId=VPC_ID,
                        DependsOn=GW_ATTACH,
                        CidrBlock=self.subnet_cidr(variables['VpcCIDR'], net_type, i),
                        #Tags=Tags(type=net_type),
                    )
                )

                # Nat gateways in public subnets, one per AZ
                if net_type == 'public':
                    nat_gateway_eip = 'NatGatewayEIP' + name_suffix
                    nat_gateway = 'NatGateway' + name_suffix
                    route_name = 'DefaultPrivateRoute' + name_suffix
                    t.add_resource(
                        ec2.EIP(
                            nat_gateway_eip,
                            Domain='vpc',
                            DependsOn=GW_ATTACH
                        )
                    )
                    t.add_resource(
                        ec2.NatGateway(
                            nat_gateway,
                            SubnetId=Ref(subnet_name),
                            AllocationId=GetAtt(nat_gateway_eip, 'AllocationId'),
                        )
                    )
                    # Default routes for private subnets through nat gateways
                    t.add_resource(
                        ec2.Route(
                            route_name,
                            #RouteTableId=Ref(route_table_name),
                            RouteTableId=Ref('PrivateRouteTable'),
                            DestinationCidrBlock='0.0.0.0/0',
                            NatGatewayId=Ref(nat_gateway),
                        )
                    )

                # Accociate each subnet to either the pub or priv route table
                t.add_resource(
                    ec2.SubnetRouteTableAssociation(
                        '%sRouteTableAssociation%s' % (name_prefix, name_suffix),
                        SubnetId=Ref(subnet_name),
                        RouteTableId=Ref(route_table_name)
                    )
                )


        # Outputs
        for net_type in net_types:
            t.add_output(Output(
                    '%sSubnets' % net_type.capitalize(),
                    Value=Join(',', [Ref(sn) for sn in subnets[net_type]])))
            for i, sn in enumerate(subnets[net_type]):
                t.add_output(Output(sn, Value=Ref(sn)))

        #t.add_output(Output(
        #        'AvailabilityZones',
        #        Value=Join(',', zones)))
        #for i, az in enumerate(zones):
        #    t.add_output(Output(
        #            'AvailabilityZone0%d' % (i +1),
        #            Value=az))
        

    def validate_custom_subnets(self):
        variables = self.get_variables()
        # compose subnet definitions list
        if variables['UseDefaultSubnets']:
            subnet_defs = DEFAULT_SUBNETS + variables['CustomSubnets']
        else:
            subnet_defs = variables['CustomSubnets']
        # validate custom subnet definitions
        public_subnets = [s['name'] for s in subnet_defs
                if 'net_type' in s and s['net_type'] == 'public']
        for subnet in variables['CustomSubnets']:
            if not 'name' in subnet:
                raise ValueError("User provided subnets must have 'name' field")
            if not 'net_type' in subnet:
                raise ValueError("User provided subnets must have 'net_type' field")
            if subnet['net_type'] not in ['public', 'private']:
                raise ValueError("Value of 'net_type' field in user provided subnets "
                                 "must be one of ['public', 'private']")
            if subnet['net_type'] == 'private':
                if not 'public_subnet' in subnet:
                    raise ValueError("User provided subnets must have 'public_subnet' "
                                     "field if 'net_type' is 'private'")
                if subnet['public_subnet'] not in public_subnets:
                    raise ValueError("'%s' is not a valid 'public_subnet' name in user "
                                     "provided subnet '%s'"
                                     % (subnet['public_subnet'], subnet['name']))
        return subnet_defs


    def availability_zones(self):
        variables = self.get_variables()
        zones = []
        for i in range(variables['AZCount']):
            #try:
            #    az = Select(i, GetAZs(''))
            az = Select(i, GetAZs(''))
            zones.append(az)
        return zones

    def create_route_tables(self, subnet_defs):
        # one route table for each subnet
        t = self.template
        variables = self.get_variables()
        for s in subnet_defs:
            route_table_name = '%sRouteTable' % s['name']
            t.add_resource(
                ec2.RouteTable(
                    #Tags=[ec2.Tag('type', net_type)],
                    route_table_name,
                    VpcId=VPC_ID,))


    def create_template(self):
        variables = self.get_variables()
        print('variables: %s' % variables)
        subnet_defs = self.validate_custom_subnets()
        print('subnet_defs: %s' % subnet_defs)
        zones = self.availability_zones()
        print('zones: %s' % zones)
        self.create_vpc()
        self.create_gateway()
        self.create_route_tables(subnet_defs)
        #self.create_network()

