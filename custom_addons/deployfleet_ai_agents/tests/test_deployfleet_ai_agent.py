from odoo.tests.common import TransactionCase, tagged

_EXPECTED_AGENT_KEYS = {
    "fleet_analyst", "dispatch_agent", "maintenance_agent",
    "finance_agent", "compliance_agent", "customer_agent",
}


@tagged("post_install", "-at_install")
class TestDeployfleetAIAgent(TransactionCase):
    def test_six_agent_personas_seeded(self):
        agents = self.env["deployfleet.ai.agent"].search([])
        self.assertEqual(set(agents.mapped("key")), _EXPECTED_AGENT_KEYS)

    def test_every_agent_has_a_routed_feature(self):
        agents = self.env["deployfleet.ai.agent"].search([])
        for agent in agents:
            self.assertTrue(agent.feature_id, f"{agent.key} has no routed feature")
            self.assertEqual(agent.feature_id.key, agent.key)

    def test_finance_agent_routes_through_financial_data_category(self):
        agent = self.env.ref("deployfleet_ai_agents.agent_finance_agent")
        self.assertEqual(agent.feature_id.data_category, "financial")
