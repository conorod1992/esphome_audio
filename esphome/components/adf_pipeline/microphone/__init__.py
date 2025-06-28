"""Microphone platform implementation as ADF-Pipeline Element."""

import esphome.codegen as cg
from esphome.components import microphone
import esphome.config_validation as cv
import inspect
from esphome.const import CONF_ID

from .. import (
    esp_adf_ns,
    ADFPipelineController,
    ADF_PIPELINE_CONTROLLER_SCHEMA,
    setup_pipeline_controller,
)

CODEOWNERS = ["@gnumpi"]
DEPENDENCIES = ["adf_pipeline", "microphone"]

CONF_GAIN_LOG_2 = "gain_log2"

ADFMicrophone = esp_adf_ns.class_(
    "ADFMicrophone", ADFPipelineController, microphone.Microphone, cg.Component
)

CONFIG_SCHEMA = microphone.MICROPHONE_SCHEMA.extend(
    {
        cv.GenerateID(): cv.declare_id(ADFMicrophone),
        cv.Optional(CONF_GAIN_LOG_2, default=0): cv.int_range(0, 7),
    }
).extend(ADF_PIPELINE_CONTROLLER_SCHEMA)


# @coroutine_with_priority(100.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_gain_log2(config[CONF_GAIN_LOG_2]))
    await cg.register_component(var, config)
    await setup_pipeline_controller(var, config)
    audio_device = {"max_channels": 1}
    if "audio_device" in inspect.signature(microphone.register_microphone).parameters:
        await microphone.register_microphone(
            var,
            config,
            audio_device=audio_device,
        )
    else:
        await microphone.register_microphone(var, config)
