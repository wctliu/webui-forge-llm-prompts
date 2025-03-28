import modules.shared as shared
import gradio as gr

from modules import scripts

def on_ui_settings():
    section = ('chatgpt_prompts', 'ChatGPT 提示词')

    shared.opts.add_option("gptp_openai_api_key", shared.OptionInfo("", "OpenAI API 密钥 (API Key)", section=section))
    shared.opts.add_option("gptp_openai_model", shared.OptionInfo("gpt-4o", "OpenAI 模型", section=section).info("支持的模型: gpt-4o 及以上"))
    shared.opts.add_option("gptp_deepl_api_url", shared.OptionInfo("https://api-free.deepl.com/v2/translate", "DeepL API 地址", section=section).info("付费账户需要改为 'https://api.deepl.com/v2/translate'"))
    shared.opts.add_option("gptp_deepl_api_key", shared.OptionInfo("", "DeepL API 密钥 (API Key)", section=section))

    # DeepSeek
    shared.opts.add_option("gptp_deepseek_api_key", shared.OptionInfo("", "DeepSeek API 密钥 (API Key)", section=section).needs_restart())
    shared.opts.add_option("gptp_deepseek_api_url", shared.OptionInfo("https://api.deepseek.com/v1", "DeepSeek API 地址", section=section))
    shared.opts.add_option("gptp_deepseek_model", shared.OptionInfo("deepseek-chat", "DeepSeek 模型名称", section=section))

    # SiliconFlow
    shared.opts.add_option("gptp_siliconflow_api_key", shared.OptionInfo("", "SiliconFlow API 密钥 (API Key)", section=section).needs_restart())
    shared.opts.add_option("gptp_siliconflow_api_url", shared.OptionInfo("https://api.siliconflow.com/v1", "SiliconFlow API 地址", section=section).info("生产环境地址"))
    shared.opts.add_option("gptp_siliconflow_model", shared.OptionInfo("Pro/deepseek-ai/DeepSeek-R1", "SiliconFlow 模型名称", section=section))

    # Hunyuan
    shared.opts.add_option("gptp_hunyuan_api_key", shared.OptionInfo("", "腾讯混元 API 密钥 (API Key) - 兼容模式", section=section).needs_restart())
    shared.opts.add_option("gptp_hunyuan_secret_id", shared.OptionInfo("", "腾讯混元 SecretId - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_hunyuan_secret_key", shared.OptionInfo("", "腾讯混元 SecretKey - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_hunyuan_api_url", shared.OptionInfo("https://hunyuan.tencentcloudapi.com", "腾讯混元 API 地址", section=section))
    shared.opts.add_option("gptp_hunyuan_model", shared.OptionInfo("hunyuan-lite", "腾讯混元模型名称", section=section))
    shared.opts.add_option("gptp_hunyuan_max_image_size", shared.OptionInfo(5, "最大图片尺寸(MB)", gr.Slider, {"minimum": 1, "maximum": 20, "step": 1}, section=section))
    shared.opts.add_option("gptp_hunyuan_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "支持的图片类型", section=section))

    # Volcengine Ark
    shared.opts.add_option("gptp_volcengine_ark_api_key", shared.OptionInfo("", "火山引擎方舟 API 密钥 (API Key) - 兼容模式", section=section).needs_restart())
    shared.opts.add_option("gptp_volcengine_ark_ak", shared.OptionInfo("", "火山引擎方舟访问密钥 (AccessKey, AK) - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_volcengine_ark_sk", shared.OptionInfo("", "火山引擎方舟私有密钥 (SecretKey, SK) - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_volcengine_ark_api_url", shared.OptionInfo("https://ark.volcengine.com/api/v1", "火山引擎方舟 API 地址", section=section))
    shared.opts.add_option("gptp_volcengine_ark_model", shared.OptionInfo("ep-20240929185643-6g4f2", "火山引擎方舟模型名称", section=section).info("默认模型ID，可在控制台查看"))
    shared.opts.add_option("gptp_volcengine_ark_max_image_size", shared.OptionInfo(5, "最大图片尺寸(MB)", gr.Slider, {"minimum": 1, "maximum": 20, "step": 1}, section=section))
    shared.opts.add_option("gptp_volcengine_ark_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "支持的图片类型", section=section))

    # Baidu Qianfan
    shared.opts.add_option("gptp_baidu_qianfan_api_key", shared.OptionInfo("", "百度千帆 API 密钥 (API Key) - 兼容模式", section=section).needs_restart())
    shared.opts.add_option("gptp_baidu_qianfan_api_key_native", shared.OptionInfo("", "百度千帆 API 密钥 (API Key) - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_baidu_qianfan_secret_key", shared.OptionInfo("", "百度千帆私有密钥 (Secret Key) - 签名模式", section=section).needs_restart())
    shared.opts.add_option("gptp_baidu_qianfan_api_url", shared.OptionInfo("https://aip.baidubce.com", "百度千帆 API 地址", section=section))
    shared.opts.add_option("gptp_baidu_qianfan_model", shared.OptionInfo("ERNIE-Bot-turbo", "百度千帆模型名称", section=section).info("支持模型: ERNIE-Bot-turbo, ERNIE-Bot 等"))
    shared.opts.add_option("gptp_baidu_qianfan_max_image_size", shared.OptionInfo(5, "最大图片尺寸(MB)", gr.Slider, {"minimum": 1, "maximum": 20, "step": 1}, section=section))
    shared.opts.add_option("gptp_baidu_qianfan_supported_image_types", shared.OptionInfo("jpg,jpeg,png", "支持的图片类型", section=section))

    # 通用图片处理设置
    shared.opts.add_option("gptp_image_compression_quality", shared.OptionInfo(85, "图片压缩质量", gr.Slider, {"minimum": 1, "maximum": 100, "step": 1}, section=section))
    shared.opts.add_option("gptp_max_image_dimension", shared.OptionInfo(1024, "最大图片尺寸(像素)", gr.Slider, {"minimum": 256, "maximum": 2048, "step": 256}, section=section))

scripts.script_callbacks.on_ui_settings(on_ui_settings)