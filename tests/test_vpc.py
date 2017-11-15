import unittest
from stacker.context import Context
from stacker.variables import Variable
from stackermods.blueprints.vpc import VPC
from stacker.blueprints.testutil import BlueprintTestCase

class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.variables = []

    def test_vpc(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = VPC('VPC', ctx)
        blueprint.resolve_variables(self.variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

if __name__ == '__main__':
    unittest.main()

