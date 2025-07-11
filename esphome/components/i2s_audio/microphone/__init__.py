import esphome.config_validation as cv
import esphome.codegen as cg
import inspect

from esphome import pins
from esphome.const import CONF_CHANNEL, CONF_ID, CONF_MODEL, CONF_NUMBER
from esphome.components import microphone, esp32
from esphome.components.adc import ESP32_VARIANT_ADC1_PIN_TO_CHANNEL, validate_adc_pin

from .. import i2s_settings as i2s

from .. import (
    i2s_audio_ns,
    I2SAudioComponent,
    I2SReader,
    CONF_I2S_ADC,
    CONF_I2S_AUDIO_ID,
    CONF_I2S_DIN_PIN,
    CONFIG_SCHEMA_ADC,
    register_i2s_reader,
)

CODEOWNERS = ["@jesserockz"]
DEPENDENCIES = ["i2s_audio"]

CONF_ADC_PIN = "adc_pin"
CONF_ADC_TYPE = "adc_type"
CONF_PDM = "pdm"
CONF_SAMPLE_RATE = "sample_rate"
CONF_BITS_PER_SAMPLE = "bits_per_sample"
CONF_USE_APLL = "use_apll"

I2SAudioMicrophone = i2s_audio_ns.class_(
    "I2SAudioMicrophone", I2SReader, microphone.Microphone, cg.Component
)

i2s_channel_fmt_t = cg.global_ns.enum("i2s_channel_fmt_t")
CHANNELS = {
    "left": i2s_channel_fmt_t.I2S_CHANNEL_FMT_ONLY_LEFT,
    "right": i2s_channel_fmt_t.I2S_CHANNEL_FMT_ONLY_RIGHT,
}
i2s_bits_per_sample_t = cg.global_ns.enum("i2s_bits_per_sample_t")
BITS_PER_SAMPLE = {
    16: i2s_bits_per_sample_t.I2S_BITS_PER_SAMPLE_16BIT,
    32: i2s_bits_per_sample_t.I2S_BITS_PER_SAMPLE_32BIT,
}

INTERNAL_ADC_VARIANTS = [esp32.const.VARIANT_ESP32]
PDM_VARIANTS = [esp32.const.VARIANT_ESP32, esp32.const.VARIANT_ESP32S3]

_validate_bits = cv.float_with_unit("bits", "bit")


def validate_esp32_variant(config):
    variant = esp32.get_esp32_variant()
    if config[CONF_ADC_TYPE] == "external":
        if config[CONF_PDM]:
            if variant not in PDM_VARIANTS:
                raise cv.Invalid(f"{variant} does not support PDM")
        return config
    if config[CONF_ADC_TYPE] == "internal":
        if variant not in INTERNAL_ADC_VARIANTS:
            raise cv.Invalid(f"{variant} does not have an internal ADC")
        return config
    raise NotImplementedError


BASE_SCHEMA = microphone.MICROPHONE_SCHEMA.extend(
    {
        cv.GenerateID(): cv.declare_id(I2SAudioMicrophone),
        cv.GenerateID(CONF_I2S_AUDIO_ID): cv.use_id(I2SAudioComponent),
        cv.Optional(CONF_CHANNEL, default="right"): cv.enum(CHANNELS),
        cv.Optional(CONF_SAMPLE_RATE, default=16000): cv.int_range(min=1),
        cv.Optional(CONF_BITS_PER_SAMPLE, default="32bit"): cv.All(
            _validate_bits, cv.enum(BITS_PER_SAMPLE)
        ),
        cv.Optional(CONF_USE_APLL, default=False): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)

CONFIG_SCHEMA = cv.All(
    cv.typed_schema(
        {
            "internal": BASE_SCHEMA.extend(
                {
                    cv.Required(CONF_ADC_PIN): validate_adc_pin,
                }
            ),
            "external": BASE_SCHEMA.extend(
                {
                    cv.Required(CONF_I2S_DIN_PIN): pins.internal_gpio_input_pin_number,
                    cv.Required(CONF_PDM): cv.boolean,
                    cv.Optional(
                        CONF_I2S_ADC, default={CONF_MODEL: "generic"}
                    ): CONFIG_SCHEMA_ADC,
                }
            ).extend(i2s.CONFIG_SCHEMA_I2S_COMMON),
        },
        key=CONF_ADC_TYPE,
    ),
    validate_esp32_variant,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # await cg.register_parented(var, config[CONF_I2S_AUDIO_ID])

    if config[CONF_ADC_TYPE] == "internal":
        variant = esp32.get_esp32_variant()
        pin_num = config[CONF_ADC_PIN][CONF_NUMBER]
        channel = ESP32_VARIANT_ADC1_PIN_TO_CHANNEL[variant][pin_num]
        cg.add(var.set_adc_channel(channel))
    else:
        # cg.add(var.set_din_pin(config[CONF_I2S_DIN_PIN]))
        # cg.add(var.set_pdm(config[CONF_PDM]))
        await register_i2s_reader(var, config)

    audio_device = {"max_channels": 1}
    if "audio_device" in inspect.signature(microphone.register_microphone).parameters:
        await microphone.register_microphone(
            var,
            config,
            audio_device=audio_device,
        )
    else:
        await microphone.register_microphone(var, config)
