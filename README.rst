________________________________________________________________________________
11/13/2017

TODO vpc.py:

tags
outputs
unittests
docs



TODO project:
rename
README.rst
pip packaging
initial release 






________________________________________________________________________________
11/7/2017

stacker runs in python2.7

pip install stacker

./conf
./conf/vpc.conf.yml
./test
./stacker_blueprints
./stacker_blueprints/vpc.py


stacker build -o -v -i conf/vpc.conf.yml 
[2017-11-07T15:41:57] INFO stacker.commands.stacker:24(configure): Using interactive AWS provider mode.
[2017-11-07T15:41:57] INFO stacker.plan:318(outline): Plan "Create/Update stacks":
[2017-11-07T15:41:57] INFO stacker.plan:326(outline):   - step: 1: target: "testvpc-vpc", action: "_launch_stack"



# just dump template to file
mkdir -p test/stack_templates/testvpc-vpc/
stacker build -v -i -r us-west-2 -d test/ conf/vpc.conf.yml

# build/update stack (interactive)
stacker build -v -i -r us-west-2 conf/vpc.conf.yml

# destroy stacks
stacker destroy -v -i -r us-west-2 conf/vpc.conf.yml
stacker destroy -v -i -r us-west-2 -f conf/vpc.conf.yml






