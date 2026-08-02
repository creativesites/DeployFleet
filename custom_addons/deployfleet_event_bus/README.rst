======================
DeployFleet Event Bus
======================

Cross-module publish/subscribe event bus. Replaces the hardcoded
if-chain-of-subscribers pattern found in the DeployGuard source (see
``docs/architecture/06-risks-and-recommendations.md`` risk #4) with a
subscriber registry: a module that wants to react to an event declares a
``deployfleet.event.subscription`` data record naming an event pattern and
a handler method — it never requires editing this module.

Publish an event from any model::

    self.env["deployfleet.event.log"].register_event(
        "vehicle.breakdown.created", "deployfleet.vehicle", vehicle.id,
        {"vehicle_name": vehicle.display_name},
    )

Subscribe from any module's data file::

    <record id="subscription_example" model="deployfleet.event.subscription">
        <field name="event_pattern">vehicle.breakdown.*</field>
        <field name="model_name">your.module.bridge</field>
        <field name="method_name">_handle_bus_event</field>
    </record>
