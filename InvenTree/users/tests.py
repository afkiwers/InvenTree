# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.apps import apps

from users.models import RuleSet


class RuleSetModelTest(TestCase):
    """
    Some simplistic tests to ensure the RuleSet model is setup correctly.
    """

    def test_ruleset_models(self):

        keys = RuleSet.RULESET_MODELS.keys()
        
        # Check if there are any rulesets which do not have models defined

        missing = [name for name in RuleSet.RULESET_NAMES if name not in keys]

        if len(missing) > 0:
            print("The following rulesets do not have models assigned:")
            for m in missing:
                print("-", m)

        # Check if models have been defined for a ruleset which is incorrect
        extra = [name for name in keys if name not in RuleSet.RULESET_NAMES]

        if len(extra) > 0:
            print("The following rulesets have been improperly added to RULESET_MODELS:")
            for e in extra:
                print("-", e)

        # Check that each ruleset has models assigned
        empty = [key for key in keys if len(RuleSet.RULESET_MODELS[key]) == 0]

        if len(empty) > 0:
            print("The following rulesets have empty entries in RULESET_MODELS:")
            for e in empty:
                print("-", e)

        self.assertEqual(len(missing), 0)
        self.assertEqual(len(extra), 0)
        self.assertEqual(len(empty), 0)

    def test_model_names(self):
        """
        Test that each model defined in the rulesets is valid,
        based on the database schema!
        """

        available_models = apps.get_models()

        available_tables = []

        for model in available_models:
            table_name = model.objects.model._meta.db_table
            available_tables.append(table_name)

        errors = 0

        assigned_models = []

        # Now check that each defined model is a valid table name
        for key in RuleSet.RULESET_MODELS.keys():

            models = RuleSet.RULESET_MODELS[key]

            for m in models:

                assigned_models.append(m)

                if m not in available_tables:
                    print("{n} is not a valid database table".format(n=m))
                    errors += 1

        self.assertEqual(errors, 0)

        missing_models = []

        for model in available_tables:
            if model not in assigned_models:
                missing_models.append(model)

        if len(missing_models) > 0:
            print("WARNING: The following database models are not covered by the define RuleSet permissions:")
            for m in missing_models:
                print("-", m)
