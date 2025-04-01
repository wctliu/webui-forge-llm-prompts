const API_CONFIG = {
  BASE_PATH: '/sdapi/chatgpt-prompts/v1',
  PATHS: {
    LIST: '/prompt/list',
    GET: '/prompt/get',
    SAVE: '/prompt/save',
    DELETE: '/prompt/delete',
    DEEPSEEK: '/deepseek',
    SILICONFLOW: '/siliconflow',
    HUNYUAN: '/hunyuan',
    HUNYUAN_NATIVE: '/hunyuan_native',
    VOLCENGINE_ARK: '/volcengine_ark',
    VOLCENGINE_ARK_NATIVE: '/volcengine_ark_native',
    BAIDU_QIANFAN: '/baidu_qianfan',
    BAIDU_QIANFAN_NATIVE: '/baidu_qianfan_native'
  }
};

window.gptp = window.gptp || {};
gptp = window.gptp;

gptp.core = (function () {
  const DEFAULT_INSTRUCTIONS = `I want you to act as a Stable Diffusion Art Prompt Generator...`;
  const API_BASE = API_CONFIG.BASE_PATH;
  const PROMPT_API = `${API_BASE}/prompt`;
  const COMPLETIONS_URL = 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions';
  const DEEPL_URL = 'gptp/translate';

  const ROLE_TYPE_SYSTEM = 'system';
  const ROLE_TYPE_USER = 'user';
  const DISPLAY_NONE = 'none';
  const DISPLAY_INLINE_BLOCK = 'inline-block';

  const RESPONSE_SCHEMA = {
    'type': 'json_schema',
    'json_schema': {
      'name': 'sd_prompt_response',
      'strict': true,
      'schema': {
        'type': 'object',
        'properties': {
          'success': { 'type': 'boolean' },
          'error': { 'type': 'string' },
          'prompts': { 'type': 'array', 'items': { 'type': 'string' } }
        },
        'required': ['success', 'error', 'prompts'],
        'additionalProperties': false
      }
    }
  };

  async function loadTags() {
    try {
      console.log('正在加载标签...');
      const response = await fetch(`${API_BASE}/prompt/list`);
      if (!response.ok) {
        console.warn('API请求失败，状态码:', response.status);
        return getDefaultTags();
      }
      const result = await response.json();
      console.log('API返回结果:', result);
      if (!result.success) {
        console.warn('API返回success为false');
        return getDefaultTags();
      }
      const formattedTags = formatTagList(result.files);
      console.log('格式化后的标签:', formattedTags);
      return formattedTags;
    } catch (error) {
      console.error('加载标签失败:', error);
      return getDefaultTags();
    }
  }

  async function saveTag(tagName, content) {
    try {
      const response = await fetch(`${API_BASE}/prompt/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: `${tagName}.txt`,
          content: content
        })
      });
      const result = await response.json();
      return result.success;
    } catch (error) {
      console.error('保存失败:', error);
      return false;
    }
  }

  function getDefaultTags() {
    return [
      { name: '默认风格', filename: '默认风格.txt' },
      { name: '动漫风格', filename: '动漫风格.txt' }
    ];
  }

  function formatTagList(files) {
    return (files || []).map(file => ({
      name: file.replace('.txt', ''),
      filename: file,
      instructions: ''
    }));
  }

  async function loadTagContent(tagName) {
    try {
      const response = await fetch(`${PROMPT_API}/get?name=${encodeURIComponent(tagName)}.txt`);
      if (!response.ok) return '';
      const result = await response.json();
      return result.success ? result.content : '';
    } catch (error) {
      console.error('加载内容失败:', error);
      return '';
    }
  }

  function removeLeadingSpaces(text) {
    return text.split('\n').map(line => line.trimStart()).join('\n');
  }

  async function doGenerate() {
    let promptElement = document.getElementById('gptp-prompt');
    let prompt = promptElement.value;
    let instructionsElement = document.getElementById('gptp-instructions');
    let messages = [];
    if (!prompt) {
      gptp.toastr.error('请提供提示词');
      return;
    }
    const apiSelector = document.getElementById('gptp-api-selector');
    const selectedApi = apiSelector.value;
    gptp.cache.set('last_used_api', selectedApi);

    const activeIndex = gptp.cache.get('selected_tag_index') || 0;
    const tags = await loadTags();

    if (!tags || tags.length === 0) {
      console.error('没有可用的标签数据');
      gptp.toastr.error('没有可用的标签配置');
      return;
    }

    const validIndex = Math.min(activeIndex, tags.length - 1);
    const activeTag = tags[validIndex];

    if (!activeTag) {
      console.error('获取当前标签失败');
      gptp.toastr.error('获取当前标签配置失败');
      return;
    }

    let instructions = await loadTagContent(activeTag.name);
    const currentInput = instructionsElement.value;

    if (!instructions.trim()) {
      instructions = DEFAULT_INSTRUCTIONS;
    }

    if (currentInput && currentInput.trim().length > 0) {
      instructions = currentInput;
    }

    console.log('当前使用的系统提示词:', instructions);

    messages.push({
      role: ROLE_TYPE_SYSTEM,
      content: instructions
    });

    messages.push({
      role: ROLE_TYPE_USER,
      content: prompt
    });

    // 显示加载动画
    const loader = document.querySelector('.gptp-loader');
    if (loader) {
      loader.style.display = 'flex';
    }

    try {
      let apiUrl, apiHeaders, apiBody;
      const imageFile = document.getElementById('gptp-image-input')?.files[0];
      let imageBase64 = '';

      if (imageFile) {
        const { fullBase64 } = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            const base64Data = e.target.result;
            resolve({ fullBase64: base64Data.split(',')[1] });
          };
          reader.onerror = reject;
          reader.readAsDataURL(imageFile);
        });
        imageBase64 = fullBase64;
      }

      switch (selectedApi) {
        case 'DeepSeek':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.DEEPSEEK}`;
          apiHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${opts.gptp_deepseek_api_key}`
          };
          apiBody = JSON.stringify({
            model: opts.gptp_deepseek_model,
            text: prompt,
            system_message: instructions,
            messages: messages,
            temperature: parseFloat(opts.gptp_deepseek_temperature || 0.7),
            max_tokens: parseInt(opts.gptp_deepseek_max_tokens || 800),
            top_p: parseFloat(opts.gptp_deepseek_top_p || 1.0)
          });
          break;

        case 'SiliconFlow':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.SILICONFLOW}`;
          apiHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${opts.gptp_siliconflow_api_key}`
          };
          apiBody = JSON.stringify({
            model: opts.gptp_siliconflow_model,
            messages: messages,
            max_tokens: parseInt(opts.gptp_siliconflow_max_tokens || 800),
            temperature: parseFloat(opts.gptp_siliconflow_temperature || 0.7),
            top_p: parseFloat(opts.gptp_siliconflow_top_p || 0.7),
            top_k: 50,
            response_format: { type: "text" }
          });
          break;

        case 'Hunyuan':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.HUNYUAN}`;
          apiHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${opts.gptp_hunyuan_api_key}`
          };

          let hunyuanContent = [{ type: "text", text: prompt }];
          if (imageBase64) {
            hunyuanContent.push({ type: "image", image_url: `data:image/jpeg;base64,${imageBase64}` });
          }

          messages = [];
          if (instructions && instructions.trim().length > 0) {
            messages.push({
              role: ROLE_TYPE_SYSTEM,
              content: instructions
            });
          }
          messages.push({
            role: ROLE_TYPE_USER,
            content: hunyuanContent
          });

          apiBody = JSON.stringify({
            model: opts.gptp_hunyuan_model,
            messages: messages,
            temperature: parseFloat(opts.gptp_hunyuan_temperature || 0.7),
            max_tokens: parseInt(opts.gptp_hunyuan_max_tokens || 800),
            top_p: parseFloat(opts.gptp_hunyuan_top_p || 1.0)
          });
          break;

        case 'HunyuanNative':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.HUNYUAN_NATIVE}`;
          apiHeaders = {
            "Content-Type": "application/json"
          };

          let hunyuanQuery = prompt;
          if (imageBase64) {
            hunyuanQuery = {
              text: prompt,
              image: imageBase64
            };
          }

          apiBody = JSON.stringify({
            model: opts.gptp_hunyuan_model,
            messages: messages,
            temperature: parseFloat(opts.gptp_hunyuan_temperature || 0.7),
            top_p: parseFloat(opts.gptp_hunyuan_top_p || 1.0),
            max_tokens: parseInt(opts.gptp_hunyuan_max_tokens || 800)
          });
          break;

        case 'VolcengineArk':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.VOLCENGINE_ARK}`;
          apiHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${opts.gptp_volcengine_ark_api_key}`
          };

          let volcengineMessages = [];
          if (instructions && instructions.trim().length > 0) {
            volcengineMessages.push({
              role: "system",
              content: instructions
            });
          }

          if (imageBase64) {
            volcengineMessages.push({
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "image", image: imageBase64 }
              ]
            });
          } else {
            volcengineMessages.push({
              role: "user",
              content: prompt
            });
          }

          apiBody = JSON.stringify({
            model: opts.gptp_volcengine_ark_model || "doubao-1-5-vision-pro-32k-250115",
            messages: volcengineMessages,
            temperature: parseFloat(opts.gptp_volcengine_ark_temperature || 0.7),
            top_p: parseFloat(opts.gptp_volcengine_ark_top_p || 1.0),
            max_tokens: parseInt(opts.gptp_volcengine_ark_max_tokens || 800)
          });
          break;

        case 'VolcengineArkNative':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.VOLCENGINE_ARK_NATIVE}`;
          apiHeaders = {
            "Content-Type": "application/json"
          };

          let volcengineArkNativeMessages = [];
          if (instructions && instructions.trim().length > 0) {
            volcengineArkNativeMessages.push({
              role: "system",
              content: instructions
            });
          }

          if (imageBase64) {
            volcengineArkNativeMessages.push({
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "image", image_url: `data:image/jpeg;base64,${imageBase64}` }
              ]
            });
          } else {
            volcengineArkNativeMessages.push({
              role: "user",
              content: prompt
            });
          }

          apiBody = JSON.stringify({
            model: opts.gptp_volcengine_ark_model || "doubao-1-5-vision-pro-32k-250115",
            messages: volcengineArkNativeMessages,
            temperature: parseFloat(opts.gptp_volcengine_ark_temperature || 0.7),
            top_p: parseFloat(opts.gptp_volcengine_ark_top_p || 1.0),
            max_tokens: parseInt(opts.gptp_volcengine_ark_max_tokens || 800),
            image_url: imageBase64 ? "placeholder" : null,
            access_key: opts.gptp_volcengine_ark_ak,
            secret_key: opts.gptp_volcengine_ark_sk
          });
          break;

        case 'BaiduQianfan':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.BAIDU_QIANFAN}`;
          apiHeaders = {
            "Content-Type": "application/json"
          };

          let baiduMessages = [];
          if (instructions && instructions.trim().length > 0) {
            baiduMessages.push({
              role: "system",
              content: instructions
            });
          }

          if (imageBase64) {
            baiduMessages.push({
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "image_url", image_url: { url: `data:image/jpeg;base64,${imageBase64}` } }
              ]
            });
          } else {
            baiduMessages.push({
              role: "user",
              content: prompt
            });
          }

          apiBody = JSON.stringify({
            model: opts.gptp_baidu_qianfan_model,
            messages: baiduMessages,
            temperature: parseFloat(opts.gptp_baidu_qianfan_temperature || 0.7),
            top_p: parseFloat(opts.gptp_baidu_qianfan_top_p || 1.0),
            max_tokens: parseInt(opts.gptp_baidu_qianfan_max_tokens || 800),
            client_id: opts.gptp_baidu_qianfan_api_key,
            client_secret: opts.gptp_baidu_qianfan_secret_key,
            image_url: imageBase64 ? "placeholder" : null
          });
          break;

        case 'BaiduQianfanNative':
          apiUrl = `${API_BASE}${API_CONFIG.PATHS.BAIDU_QIANFAN_NATIVE}`;
          apiHeaders = {
            "Content-Type": "application/json"
          };

          let baiduNativeMessages = [];
          if (instructions && instructions.trim().length > 0) {
            baiduNativeMessages.push({
              role: "system",
              content: instructions
            });
          }

          if (imageBase64) {
            baiduNativeMessages.push({
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "image_url", image_url: { url: `data:image/jpeg;base64,${imageBase64}` } }
              ]
            });
          } else {
            baiduNativeMessages.push({
              role: "user",
              content: prompt
            });
          }

          apiBody = JSON.stringify({
            model: opts.gptp_baidu_qianfan_model,
            messages: baiduNativeMessages,
            temperature: parseFloat(opts.gptp_baidu_qianfan_temperature || 0.7),
            top_p: parseFloat(opts.gptp_baidu_qianfan_top_p || 1.0),
            max_tokens: parseInt(opts.gptp_baidu_qianfan_max_tokens || 800),
            client_id: opts.gptp_baidu_qianfan_api_key_native,
            client_secret: opts.gptp_baidu_qianfan_secret_key,
            image_url: imageBase64 ? "placeholder" : null
          });
          break;

        default:
          apiUrl = 'https://api.openai.com/v1/chat/completions';
          apiHeaders = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${opts.gptp_openai_api_key}`
          };
          apiBody = JSON.stringify({
            model: opts.gptp_openai_model,
            messages: messages,
            response_format: RESPONSE_SCHEMA
          });
      }

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: apiHeaders,
        body: apiBody
      });

      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      let content = '';

      if (selectedApi.endsWith('Native')) {
        content = data.response || data.result || data.text || '';
        if (!content && data.error_code) {
          throw new Error(data.error_msg || 'API未返回有效内容');
        }
      } else if (['DeepSeek', 'SiliconFlow', 'Hunyuan', 'VolcengineArk', 'BaiduQianfan'].includes(selectedApi)) {
        content = data.text || data.result || '';
        if (!content && data.error) {
          throw new Error(data.error || 'API未返回有效内容');
        }
      } else {
        const rawContent = data.choices?.[0]?.message?.content || '';
        try {
          const parsedContent = JSON.parse(rawContent);
          content = parsedContent.prompts.join('\n');
        } catch (e) {
          content = rawContent;
        }
      }

      const cleanedContent = content.replace(/^"(.*)"$/, '$1');
      const displayContent = cleanedContent || content;
      const suffix = document.getElementById('gptp-suffix').value.trim();
      const fullPrompt = suffix ? `${displayContent} ${suffix}` : displayContent;
      
      document.getElementById('gptp-response').innerHTML = `
        <div class="gptp-response-row">
          <span>${fullPrompt}</span>
          <button onclick="gptp.core.applyPrompt(event)">Apply</button>
        </div>
      `;
    } catch (error) {
      console.error(error);
      gptp.toastr.error(error.message);
      document.getElementById('gptp-response').innerHTML = `
        <div class="gptp-response-row">${error.message}</div>
      `;
    } finally {
      // 隐藏加载动画
      const loader = document.querySelector('.gptp-loader');
      if (loader) {
        loader.style.display = 'none';
      }
    }
  }

  function toggleInstructions() {
    let instructions = document.getElementById('gptp-instructions');
    let showBtnOff = document.getElementById('gptp-show-instructions-btn-off');
    let showBtnOn = document.getElementById('gptp-show-instructions-btn-on');
    if (instructions.style.display === DISPLAY_NONE) {
      instructions.style.display = DISPLAY_INLINE_BLOCK;
      showBtnOff.style.display = DISPLAY_NONE;
      showBtnOn.style.display = DISPLAY_INLINE_BLOCK;
    } else {
      instructions.style.display = DISPLAY_NONE;
      showBtnOff.style.display = DISPLAY_INLINE_BLOCK;
      showBtnOn.style.display = DISPLAY_NONE;
    }
    gptp.cache.set('toggle-instructions', showBtnOn.style.display === DISPLAY_INLINE_BLOCK ? 1 : 0);
  }

  function readImageFile(file) {
    return new Promise((resolve, reject) => {
      if (!file.type.match('image/(jpeg|png|webp)')) {
        reject('仅支持JPEG/PNG/WEBP格式');
        return;
      }
      if (file.size > opts.gptp_hunyuan_max_image_size * 1024 * 1024) {
        reject(`图片需小于${opts.gptp_hunyuan_max_image_size}MB`);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.readAsDataURL(file);
    });
  }

  function toggleTranslation() {
    let translateBtnOff = document.getElementById('gptp-show-translation-btn-off');
    let translateBtnOn = document.getElementById('gptp-show-translation-btn-on');
    if (translateBtnOff.style.display === DISPLAY_NONE) {
      translateBtnOff.style.display = DISPLAY_INLINE_BLOCK;
      translateBtnOn.style.display = DISPLAY_NONE;
    } else {
      translateBtnOffVL = DISPLAY_NONE;
      translateBtnOn.style.display = DISPLAY_INLINE_BLOCK;
    }
    gptp.cache.set('toggle-translation', translateBtnOn.style.display === DISPLAY_INLINE_BLOCK ? 1 : 0);
  }

  function isTranslationEnabled() {
    return (
      opts.gptp_deepl_api_key &&
      opts.gptp_deepl_api_key.trim().length &&
      document.getElementById('gptp-show-translation-btn-on').style.display === DISPLAY_INLINE_BLOCK
    );
  }

  function showMissingAPIKeyDialog() {
    gptp.dialog.show({
      title: 'OpenAI API Key Required',
      content: `
        Please provide an OpenAI API key in the extension settings to use this feature.
        You can find documentation on how to get an API key below.
      `,
      buttons: [
        {
          text: 'Documentation',
          action: function () {
            window.open('https://github.com/ilian6806/stable-diffusion-webui-chat-gpt-prompts/wiki', '_blank');
          }
        },
        {
          text: 'Close'
        }
      ]
    });
  }

  function showGPTDialog() {
    const lastUsedApi = gptp.cache.get('last_used_api') || 'DeepSeek';
    const apiType = document.getElementById('gptp-api-selector')?.value || 'DeepSeek';
    const instructionsElement = document.getElementById('gptp-instructions');
    const checkApiKey = (type) => {
      const apiKeyMap = {
        OpenAI: ['gptp_openai_api_key'],
        Anthropic: ['gptp_anthropic_api_key'],
        DeepSeek: ['gptp_deepseek_api_key'],
        SiliconFlow: ['gptp_siliconflow_api_key'],
        Custom: ['gptp_custom_api_key'],
        Hunyuan: ['gptp_hunyuan_api_key'],
        HunyuanNative: ['gptp_hunyuan_secret_id', 'gptp_hunyuan_secret_key'],
        VolcengineArk: ['gptp_volcengine_ark_api_key'],
        VolcengineArkNative: ['gptp_volcengine_ark_ak', 'gptp_volcengine_ark_sk'],
        BaiduQianfan: ['gptp_baidu_qianfan_api_key', 'gptp_baidu_qianfan_secret_key'],
        BaiduQianfanNative: ['gptp_baidu_qianfan_api_key_native', 'gptp_baidu_qianfan_secret_key']
      };

      const keys = apiKeyMap[type];
      if (!keys) return false;

      // 如果需要检查多个键
      if (Array.isArray(keys)) {
        for (const key of keys) {
          if (!opts[key] || opts[key].trim() === '') {
            // 提示用户需要配置哪些键
            let configMessage = `请在设置中配置 ${type} 所需的`;
            if (type === 'HunyuanNative') {
              configMessage += " SecretId 和 SecretKey";
            } else if (type === 'VolcengineArkNative') {
              configMessage += " AccessKey(AK) 和 SecretKey(SK)";
            } else if (type === 'BaiduQianfan' || type === 'BaiduQianfanNative') {
              configMessage += " API Key 和 Secret Key";
            } else {
              configMessage += ` ${key}`;
            }
            document.querySelector('#gptp-error-message').textContent = configMessage;
            return false;
          }
        }
        return true;
      }
      
      // 单个键的情况
      if (!opts[keys[0]] || opts[keys[0]].trim() === '') {
        document.querySelector('#gptp-error-message').textContent = `请在设置中配置 ${keys[0]}`;
        return false;
      }
      return true;
    };

    if (!checkApiKey(apiType)) {
      let missingKeys = '';
      if (apiType === 'HunyuanNative') {
        missingKeys = '请配置 SecretId 和 SecretKey';
      } else if (apiType === 'VolcengineArkNative') {
        missingKeys = '请配置 AccessKey(AK) 和 SecretKey(SK)';
      } else if (apiType === 'BaiduQianfanNative') {
        missingKeys = '请配置 API Key 和 Secret Key';
      } else {
        missingKeys = '请配置 API Key';
      }
      
      gptp.dialog.show({
        title: `${apiType} 配置缺失`,
        content: `请前往设置界面进行配置：${missingKeys}`,
        buttons: []
      });
      return;
    }

    let content = {
      instructions: gptp.cache.get('instructions') || removeLeadingSpaces(DEFAULT_INSTRUCTIONS),
      prompt: gptp.cache.get('prompt') || '',
      response: gptp.cache.get('response') || '',
      suffix: gptp.cache.get('suffix') || ''
    };

    let translateSwitchDisplay = opts.gptp_deepl_api_key.trim().length ? 'inline-block' : 'none';

    gptp.dialog.show({
      title: 'ChatGPT Prompts',
      content: `
        <style>
          .gptp-dialog {
            background: #1a1b1e;
            color: #e0e0e0;
          }
          .gptp-loader {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
          }
          .gptp-loader-container {
            background: #2a2b2e;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
          }
          .gptp-loader-spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #2a2b2e;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: gptp-spin 1s linear infinite;
            margin: 0 auto 1rem;
          }
          .gptp-loader-text {
            font-size: 1.2rem;
            color: #e0e0e0;
          }
          @keyframes gptp-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .gptp-media-section {
            margin: 1rem 0;
            padding: 1.5rem;
            border: 1px solid #3a3b3e;
            border-radius: 8px;
            background: #2a2b2e;
          }
          .gptp-media-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 0.8rem 1.2rem;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1rem;
            transition: background 0.2s;
          }
          .gptp-media-btn:hover {
            background: #2980b9;
          }
          .gptp-media-btn svg {
            width: 24px;
            height: 24px;
            fill: currentColor;
          }
          .gptp-media-preview {
            margin-top: 1rem;
          }
          .gptp-preview-container {
            position: relative;
            margin: 1rem 0;
            border: 1px solid #3a3b3e;
            border-radius: 8px;
            padding: 1rem;
            background: #2a2b2e;
          }
          .gptp-preview-image {
            max-width: 100%;
            max-height: 200px;
            display: block;
            margin: 0 auto;
            border-radius: 4px;
          }
          .gptp-preview-meta {
            margin-top: 1rem;
            font-size: 0.9rem;
            color: #b0b0b0;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          .gptp-image-delete-btn {
            background: none;
            border: none;
            color: #ff4444;
            cursor: pointer;
            font-size: 1.2rem;
            padding: 0.4rem 0.8rem;
            border-radius: 4px;
            transition: all 0.2s;
          }
          .gptp-image-delete-btn:hover {
            background: rgba(255, 68, 68, 0.1);
            color: #ff6666;
          }
          .gptp-api-selector {
            margin-bottom: 1.5rem;
          }
          .gptp-api-selector select {
            width: 100%;
            padding: 0.8rem;
            border: 1px solid #3a3b3e;
            border-radius: 6px;
            background: #2a2b2e;
            color: #e0e0e0;
            font-size: 1rem;
            cursor: pointer;
            transition: border-color 0.2s;
          }
          .gptp-api-selector select:focus {
            outline: none;
            border-color: #3498db;
          }
          .gptp-api-selector select option {
            background: #2a2b2e;
            color: #e0e0e0;
          }
          .gptp-api-selector select optgroup {
            background: #1a1b1e;
            color: #b0b0b0;
            font-weight: bold;
          }
          .gptp-tab-container {
            margin: 1rem 0;
            border-bottom: 1px solid #3a3b3e;
          }
          .gptp-tabs {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
          }
          .gptp-tab {
            padding: 0.6rem 1rem;
            background: #2a2b2e;
            border: 1px solid #3a3b3e;
            border-radius: 6px;
            color: #b0b0b0;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .gptp-tab:hover {
            background: #3a3b3e;
            color: #e0e0e0;
          }
          .gptp-tab.active {
            background: #3498db;
            border-color: #3498db;
            color: white;
          }
          .gptp-tab-close {
            font-size: 1.2rem;
            line-height: 1;
            padding: 0 4px;
            border-radius: 4px;
          }
          .gptp-tab-close:hover {
            background: rgba(255, 255, 255, 0.1);
          }
          .gptp-tab-add {
            background: #2a2b2e;
            border: 1px solid #3a3b3e;
            color: #b0b0b0;
            padding: 0.6rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
          }
          .gptp-tab-add:hover {
            background: #3a3b3e;
            color: #e0e0e0;
          }
          .gptp-instructions {
            margin: 1rem 0;
            padding: 1rem;
            background: #2a2b2e;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          .gptp-instructions span {
            color: #b0b0b0;
          }
          .gptp-icon {
            width: 20px;
            height: 20px;
            fill: currentColor;
            cursor: pointer;
            transition: color 0.2s;
          }
          .gptp-icon:hover {
            color: #3498db;
          }
          .gptp-textarea {
            width: 100%;
            margin: 0.5rem 0;
            padding: 1rem;
            background: #2a2b2e;
            border: 1px solid #3a3b3e;
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 1rem;
            resize: vertical;
            transition: border-color 0.2s;
          }
          .gptp-textarea:focus {
            outline: none;
            border-color: #3498db;
          }
          .gptp-textarea::placeholder {
            color: #808080;
          }
          .gptp-response {
            margin-top: 1rem;
          }
          .gptp-response-row {
            padding: 1rem;
            background: #2a2b2e;
            border: 1px solid #3a3b3e;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
          }
          .gptp-response-row span {
            flex: 1;
            color: #e0e0e0;
          }
          .gptp-response-row button {
            background: #3498db;
            color: white;
            border: none;
            padding: 0.6rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
          }
          .gptp-response-row button:hover {
            background: #2980b9;
          }
          .gptp-button-danger {
            background: #e74c3c !important;
          }
          .gptp-button-danger:hover {
            background: #c0392b !important;
          }
          /* 滚动条样式 */
          .gptp-scrollbar::-webkit-scrollbar {
            width: 8px;
            height: 8px;
          }
          .gptp-scrollbar::-webkit-scrollbar-track {
            background: #2a2b2e;
            border-radius: 4px;
          }
          .gptp-scrollbar::-webkit-scrollbar-thumb {
            background: #3a3b3e;
            border-radius: 4px;
          }
          .gptp-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #4a4b4e;
          }
        </style>
        <div class="gptp-loader">
          <div class="gptp-loader-container">
            <div class="gptp-loader-spinner"></div>
            <div class="gptp-loader-text">正在生成提示词，请稍候...</div>
          </div>
        </div>
        <div class="gptp-api-selector">
          <select id="gptp-api-selector" class="gptp-select">
            <optgroup label="通用API">
              <option value="OpenAI" ${lastUsedApi === 'OpenAI' ? 'selected' : ''}>OpenAI</option>
              <option value="DeepSeek" ${lastUsedApi === 'DeepSeek' ? 'selected' : ''}>DeepSeek</option>
              <option value="SiliconFlow" ${lastUsedApi === 'SiliconFlow' ? 'selected' : ''}>SiliconFlow</option>
            </optgroup>
            <optgroup label="腾讯混元">
              <option value="Hunyuan" ${lastUsedApi === 'Hunyuan' ? 'selected' : ''}>兼容模式</option>
              <option value="HunyuanNative" ${lastUsedApi === 'HunyuanNative' ? 'selected' : ''}>签名模式</option>
            </optgroup>
            <optgroup label="火山方舟">
              <option value="VolcengineArk" ${lastUsedApi === 'VolcengineArk' ? 'selected' : ''}>兼容模式</option>
              <option value="VolcengineArkNative" ${lastUsedApi === 'VolcengineArkNative' ? 'selected' : ''}>签名模式</option>
            </optgroup>
            <optgroup label="百度千帆">
              <option value="BaiduQianfan" ${lastUsedApi === 'BaiduQianfan' ? 'selected' : ''}>兼容模式</option>
              <option value="BaiduQianfanNative" ${lastUsedApi === 'BaiduQianfanNative' ? 'selected' : ''}>签名模式</option>
            </optgroup>
          </select>
        </div>
        <div class="gptp-media-section" style="display: none;">
          <div class="gptp-upload-group">
            <input type="file" id="gptp-image-input" accept="image/jpeg, image/png, image/webp" style="display: none;">
            <button onclick="document.getElementById('gptp-image-input').click()" class="gptp-media-btn">
              <svg class="gptp-icon" viewBox="0 0 24 24"><path d="M19 5v14H5V5h14m0-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-8 12l-3-4-3 5h12l-3-4z"/></svg>
              添加图片（可选）
            </button>
            <div id="gptp-media-preview" class="gptp-media-preview"></div>
          </div>
        </div>
        <div class="gptp-tab-container">
          <div class="gptp-tab-header">
            <div class="gptp-tabs" id="gptp-tabs"></div>
            <button class="gptp-tab-add" onclick="gptp.core.showTagManager()">+</button>
          </div>
        </div>
        <div class="gptp-instructions">
          <div>
            <div style="display: ${translateSwitchDisplay}">
              <span>Translate Prompt</span>
              <svg id="gptp-show-translation-btn-on" class="gptp-icon gptp-translation-btn" style="display: none;" viewBox="0 0 576 512">
                <path d="M192 64C86 64 0 150 0 256S86 448 192 448l192 0c106 0 192-86 192-192s-86-192-192-192L192 64zm192 96a96 96 0 1 1 0 192 96 96 0 1 1 0-192z"/>
              </svg>
              <svg id="gptp-show-translation-btn-off" class="gptp-icon gptp-translation-btn" viewBox="0 0 576 512">
                <path d="M384 128c70.7 0 128 57.3 128 128s-57.3 128-128 128l-192 0c-70.7 0-128-57.3-128-128s57.3-128 128-128l192 0zM576 256c0-106-86-192-192-192L192 64C86 64 0 150 0 256S86 448 192 448l192 0c106 0 192-86 192-192zM192 352a96 96 0 1 0 0-192 96 96 0 1 0 0 192z"/>
              </svg>
            </div>
            <span>Show Instructions</span>
            <svg id="gptp-show-instructions-btn-on" class="gptp-icon gptp-instructions-btn" style="display: none;" viewBox="0 0 576 512">
              <path d="M192 64C86 64 0 150 0 256S86 448 192 448l192 0c106 0 192-86 192-192s-86-192-192-192L192 64zm192 96a96 96 0 1 1 0 192 96 96 0 1 1 0-192z"/>
            </svg>
            <svg id="gptp-show-instructions-btn-off" class="gptp-icon gptp-instructions-btn" viewBox="0 0 576 512">
              <path d="M384 128c70.7 0 128 57.3 128 128s-57.3 128-128 128l-192 0c-70.7 0-128-57.3-128-128s57.3-128 128-128l192 0zM576 256c0-106-86-192-192-192L192 64C86 64 0 150 0 256S86 448 192 448l192 0c106 0 192-86 192-192zM192 352a96 96 0 1 0 0-192 96 96 0 1 0 0 192z"/>
            </svg>
          </div>
        </div>
        <textarea id="gptp-instructions" class="gptp-prompt gptp-textarea gptp-scrollbar" style="display: none;" rows="20">${content.instructions}</textarea>
        <textarea id="gptp-prompt" class="gptp-prompt gptp-textarea gptp-scrollbar" placeholder="Type your prompt topic..." rows="4">${content.prompt}</textarea>
        <textarea id="gptp-suffix" class="gptp-textarea gptp-scrollbar" placeholder="追加内容（自动添加到提示词末尾）..." rows="2">${content.suffix}</textarea>
        <div id="gptp-response">${content.response}</div>
      `,
      big: true,
      buttons: [
        {
          text: 'Generate',
          action: doGenerate,
          className: 'gptp-button-danger',
          dontClose: true
        },
        {
          text: 'Cancel'
        }
      ],
      onBeforeClose: function () {
        gptp.loader.hide();
        gptp.cache.set('instructions', document.getElementById('gptp-instructions').value);
        gptp.cache.set('response', document.getElementById('gptp-response').innerHTML);
        gptp.cache.set('prompt', document.getElementById('gptp-prompt').value);
        gptp.cache.set('suffix', document.getElementById('gptp-suffix').value);
        const instructionsValue = document.getElementById('gptp-instructions').value;
        const instructionsElement = document.getElementById('gptp-instructions');
        gptp.cache.set('instructions', instructionsValue);
        syncCurrentTagInstructions();
      }
    }).bindEvents({
      click: {
        '.gptp-instructions-btn': toggleInstructions,
        '.gptp-translation-btn': toggleTranslation
      },
      input: {
        '.gptp-prompt': function () {
          gptp.cache.set('prompt', this.value);
          syncCurrentTagInstructions();
        },
        '.gptp-instructions': function () {
          gptp.cache.set('instructions', this.value);
          syncCurrentTagInstructions();
        }
      }
    });

    // 在对话框显示后渲染标签
    setTimeout(() => {
      renderTags(gptp.cache.get('selected_tag_index') || 0);
    }, 100);

    if (gptp.cache.get('toggle-instructions')) {
      toggleInstructions();
    }
    if (gptp.cache.get('toggle-translation')) {
      toggleTranslation();
    }
    if (instructionsElement) {
      gptp.cache.set('instructions', instructionsElement.value);
    }

    // 初始化图片上传功能
    const imageInput = document.getElementById('gptp-image-input');
    if (imageInput) {
      imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // 验证文件类型
        if (!file.type.match(/image\/(jpeg|png|webp)/)) {
          gptp.toastr.error('仅支持JPEG/PNG/WEBP格式');
          e.target.value = '';
          return;
        }
        
        // 验证文件大小
        const maxSize = (opts.gptp_hunyuan_max_image_size || 5) * 1024 * 1024;
        if (file.size > maxSize) {
          gptp.toastr.error(`图片大小不能超过${opts.gptp_hunyuan_max_image_size}MB`);
          e.target.value = '';
          return;
        }
        
        // 预览图片
        const reader = new FileReader();
        reader.onload = function(e) {
          const preview = document.getElementById('gptp-media-preview');
          preview.innerHTML = `
            <div class="gptp-preview-container">
              <img src="${e.target.result}" class="gptp-preview-image">
              <div class="gptp-preview-meta">
                ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)
                <button class="gptp-delete-btn gptp-image-delete-btn" onclick="gptp.core.removeUploadedImage(event)">×</button>
              </div>
            </div>
          `;
        };
        reader.readAsDataURL(file);
      });
    }

    // 初始化API选择器
    const apiSelector = document.getElementById('gptp-api-selector');
    if (apiSelector) {
      apiSelector.value = lastUsedApi;
      const mediaSection = document.querySelector('.gptp-media-section');
      if (mediaSection) {
        const multimodalApis = ['Hunyuan', 'HunyuanNative', 'VolcengineArk', 'VolcengineArkNative', 'BaiduQianfan', 'BaiduQianfanNative'];
        mediaSection.style.display = multimodalApis.includes(lastUsedApi) ? 'block' : 'none';
      }
      apiSelector.addEventListener('change', function() {
        const selectedApi = this.value;
        const mediaSection = document.querySelector('.gptp-media-section');
        if (mediaSection) {
          const multimodalApis = ['Hunyuan', 'HunyuanNative', 'VolcengineArk', 'VolcengineArkNative', 'BaiduQianfan', 'BaiduQianfanNative'];
          mediaSection.style.display = multimodalApis.includes(selectedApi) ? 'block' : 'none';
        }
        gptp.cache.set('last_used_api', selectedApi);
      });
    }
  }

  function applyPrompt(e) {
    gptp.dialog.hide();
    const button = e.target;
    const previousSibling = button.previousElementSibling;
    const prompt = previousSibling.textContent;
    const element = gradioApp().querySelector("#txt2img_prompt textarea");
    gptp.utils.setValue(element, prompt, 'input');
    gptp.utils.setValue(element, prompt, 'change');
  }

  function createHeaderButton(title, text, className, style, action) {
    const button = gptp.utils.html.create('button', {
      title: title,
      innerHTML: text,
      className: className,
    }, style);
    if (action) {
      button.addEventListener('click', action);
    }
    return button;
  }

  let gptpUIInitialized = false;

  function loadUI() {
    try {
      if (gptpUIInitialized) return;
      const quicksettingsPanel = document.querySelector('#quicksettings > .wrap-inner') ||
        document.getElementById('quicksettings') ||
        document.querySelector('.gradio-container .quicksettings') ||
        document.querySelector('#quicksettings .gradio-row');
      if (!quicksettingsPanel) {
        console.warn("无法定位到快速设置面板，将在1秒后重试");
        if ((gptp.retryCount || 0) < 10) {
          gptp.retryCount = (gptp.retryCount || 0) + 1;
          setTimeout(loadUI, 1000);
        } else {
          console.error("达到最大重试次数，无法添加扩展按钮");
        }
        return;
      }
      if (!document.getElementById('gptp-main-button')) {
        const mainButton = createHeaderButton(
          'ChatGPT Prompts',
          "✨",
          'lg secondary gradio-button tool svelte-cmf5ev',
          { id: 'gptp-main-button' },
          showGPTDialog
        );
        const settingsButton = createHeaderButton(
          'ChatGPT Prompts Settings',
          "⚙️",
          'lg secondary gradio-button tool svelte-cmf5ev',
          { id: 'gptp-settings-button' },
          showSettingsDialog
        );
        quicksettingsPanel.appendChild(mainButton);
        quicksettingsPanel.appendChild(settingsButton);
        gptpUIInitialized = true;
        console.log('扩展按钮成功添加');
      }
    } catch (e) {
      console.error('扩展按钮加载失败:', e);
      setTimeout(loadUI, 5000);
    }
  }

  function init() {
    if (!gptp.cache.get('last_used_api')) {
      gptp.cache.set('last_used_api', 'DeepSeek');
    }
    if (!gptp.cache.get('selected_tag_index')) {
      gptp.cache.set('selected_tag_index', 0);
    }

    const initUI = async () => {
      try {
        const apiCheck = await fetch(`${API_BASE}/prompt/list`);
        if (!apiCheck.ok) {
          console.error('API不可用:', apiCheck.status);
          return;
        }
        await loadUI();
        await renderTags();
        setupAutoSave();
      } catch (error) {
        console.error('初始化失败:', error);
        setTimeout(initUI, 5000);
      }
    };

    if (document.readyState === 'complete') {
      initUI();
    } else {
      document.addEventListener('DOMContentLoaded', initUI);
      window.addEventListener('load', initUI);
    }
  }

  async function renderTags(selectedIndex = 0) {
    try {
      const container = document.getElementById('gptp-tabs');
      if (!container) {
        console.warn('标签容器未找到，将在对话框打开后重试');
        return;
      }
      const tags = await loadTags();
      console.log('渲染标签:', tags);
      if (!tags?.length) {
        console.warn('没有可用的标签数据');
        container.innerHTML = '<div class="gptp-no-tags">暂无标签</div>';
        return;
      }
      selectedIndex = Math.max(0, Math.min(selectedIndex, tags.length - 1));
      container.innerHTML = tags.map((tag, index) => `
        <div class="gptp-tab ${index === selectedIndex ? 'active' : ''}" 
          data-index="${index}"
          onclick="gptp.core.selectTag(${index})">
          ${tag.name}
          <span class="gptp-tab-close" 
            onclick="event.stopPropagation();gptp.core.deleteTag('${tag.name}')">×</span>
        </div>
      `).join('');
      gptp.cache.set('selected_tag_index', selectedIndex);
    } catch (error) {
      console.error('渲染标签失败:', error);
    }
  }

  async function syncCurrentTagInstructions() {
    try {
      const instructionsElement = document.getElementById('gptp-instructions');
      if (!instructionsElement) return;
      const activeIndex = gptp.cache.get('selected_tag_index') || 0;
      const tags = await loadTags();
      const currentInstructions = instructionsElement.value;
      if (tags[activeIndex]) {
        await saveTag(tags[activeIndex].name, currentInstructions);
      }
    } catch (error) {
      console.error('同步标签指令失败:', error);
    }
  }

  function setupAutoSave() {
    setInterval(() => {
      if (document.getElementById('gptp-instructions')) {
        syncCurrentTagInstructions();
      }
    }, 30000);

    const instructionsElement = document.getElementById('gptp-instructions');
    if (instructionsElement) {
      instructionsElement.addEventListener('input', debounce(() => {
        syncCurrentTagInstructions();
      }, 1000));
    }
  }

  function debounce(func, wait) {
    let timeout;
    return function () {
      const context = this, args = arguments;
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        func.apply(context, args);
      }, wait);
    };
  }

  async function selectTag(index) {
    const tags = await loadTags();
    if (index >= tags.length) return;
    const tagName = tags[index].name;
    const content = await loadTagContent(tagName);
    document.getElementById('gptp-instructions').value = content;
    gptp.cache.set('selected_tag_index', index);
    document.querySelectorAll('.gptp-tab').forEach(tab =>
      tab.classList.remove('active')
    );
    document.querySelector(`.gptp-tab[data-index="${index}"]`).classList.add('active');
  }

  async function checkTagExists(tagName) {
    try {
      const response = await fetch(`${API_BASE}/prompt/list`);
      const result = await response.json();
      if (result.success) {
        return result.files.includes(`${tagName}.txt`);
      }
      return false;
    } catch (error) {
      console.error('检查标签存在失败:', error);
      return false;
    }
  }

  async function renameTag(oldName, newName) {
    if (!newName || newName.trim() === '') {
      gptp.toastr.error('标签名不能为空');
      return false;
    }
    try {
      const contentResponse = await fetch(`${API_BASE}/prompt/get?name=${encodeURIComponent(oldName)}.txt`);
      const contentResult = await contentResponse.json();
      if (!contentResult.success) {
        throw new Error('获取标签内容失败');
      }
      if (await checkTagExists(newName)) {
        gptp.toastr.error(`标签"${newName}"已存在`);
        return false;
      }
      const saveResponse = await fetch(`${API_BASE}/prompt/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: `${newName}.txt`,
          content: contentResult.content
        })
      });
      const saveResult = await saveResponse.json();
      if (!saveResult.success) {
        throw new Error('创建新标签失败');
      }
      const deleteResponse = await fetch(`${API_BASE}/prompt/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: `${oldName}.txt`
        })
      });
      const deleteResult = await deleteResponse.json();
      if (!deleteResult.success) {
        throw new Error('删除旧标签失败');
      }
      return true;
    } catch (error) {
      console.error('重命名标签失败:', error);
      gptp.toastr.error(`重命名失败: ${error.message}`);
      return false;
    }
  }

  async function saveAllTagsFromManager() {
    try {
      const tagItems = document.querySelectorAll('#gptp-tag-manager .gptp-tag-item');
      const tags = await loadTags();
      for (let i = 0; i < Math.min(tagItems.length - 1, tags.length); i++) {
        const input = tagItems[i].querySelector('.gptp-tag-name');
        const oldName = tags[i].name;
        const newName = input.value.trim();
        if (oldName !== newName) {
          await renameTag(oldName, newName);
        }
      }
      await renderTags();
      gptp.toastr.success('标签已保存');
    } catch (error) {
      console.error('保存标签失败:', error);
      gptp.toastr.error(`保存失败: ${error.message}`);
    }
  }

  async function showTagManager() {
    const tags = await loadTags();
    gptp.dialog.show({
      title: '管理预设标签',
      content: `
        <div id="gptp-tag-manager">
          ${tags.map((tag, index) => `
            <div class="gptp-tag-item">
              <input type="text" 
                class="gptp-tag-name" 
                value="${tag.name}" 
                data-index="${index}">
              <button onclick="gptp.core.deleteTag('${tag.name}')">删除</button>
            </div>
          `).join('')}
          <div class="gptp-tag-item">
            <input type="text" id="gptp-new-tag-name" class="gptp-tag-name" placeholder="新标签名称">
            <button onclick="gptp.core.addNewTag()">添加</button>
          </div>
        </div>
      `,
      buttons: [{
        text: '保存',
        action: async function () {
          await saveAllTagsFromManager();
          gptp.dialog.hide();
        },
        className: 'gptp-button-primary'
      }]
    });
  }

  async function addNewTag() {
    const newName = document.getElementById('gptp-new-tag-name').value.trim();
    if (!newName) {
      gptp.toastr.error('请输入标签名称');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/prompt/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: `${newName}.txt`,
          content: DEFAULT_INSTRUCTIONS
        })
      });
      if (response.ok) {
        gptp.toastr.success(`标签"${newName}"已添加`);
        renderTags();
      } else {
        throw new Error('保存失败');
      }
    } catch (error) {
      gptp.toastr.error(`添加标签失败: ${error.message}`);
    }
  }

  async function deleteTag(tagName) {
    try {
      const confirm = await new Promise((resolve) => {
        gptp.dialog.show({
          title: '确认删除',
          content: `确定要删除标签"${tagName}"吗？`,
          buttons: [
            {
              text: '删除',
              action: () => resolve(true),
              className: 'gptp-button-danger'
            },
            {
              text: '取消',
              action: () => resolve(false)
            }
          ]
        });
      });
      if (!confirm) return;
      const response = await fetch(`${API_BASE}/prompt/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: `${tagName}.txt`
        })
      });
      const result = await response.json();
      if (result.success) {
        gptp.toastr.success(`标签"${tagName}"已删除`);
        await renderTags();
      } else {
        throw new Error(result.error || '删除失败');
      }
    } catch (error) {
      console.error('删除标签失败:', error);
      gptp.toastr.error(`删除标签失败: ${error.message}`);
    }
  }

  function renderPrompts(prompts) {
    document.getElementById('gptp-response').innerHTML = prompts.map(prompt => `
      <div class="gptp-response-row">
        <span>${prompt}</span>
        <button onclick="gptp.core.applyPrompt(event)">Apply</button>
      </div>
    `).join('');
  }

  function showError(error) {
    gptp.toastr.error(error);
    document.getElementById('gptp-response').innerHTML = `
      <div class="gptp-response-row">${error}</div>
    `;
  }

  function showSettingsDialog() {
    gptp.dialog.show({
      title: 'ChatGPT Prompts 设置',
      content: `
        <style>
          .gptp-settings {
            padding: 1rem;
            background: #1a1b1e;
            color: #e0e0e0;
          }
          .gptp-settings-group {
            margin-bottom: 2rem;
            padding: 1rem;
            background: #2a2b2e;
            border: 1px solid #3a3b3e;
            border-radius: 8px;
          }
          .gptp-settings-group h3 {
            margin: 0 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #3a3b3e;
            color: #e0e0e0;
            font-size: 1.1rem;
          }
          .gptp-settings-row {
            margin-bottom: 1rem;
          }
          .gptp-settings-row label {
            display: block;
            margin-bottom: 0.5rem;
            color: #b0b0b0;
          }
          .gptp-settings-row input {
            width: 100%;
            padding: 0.8rem;
            background: #1a1b1e;
            border: 1px solid #3a3b3e;
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 1rem;
            transition: border-color 0.2s;
          }
          .gptp-settings-row input:focus {
            outline: none;
            border-color: #3498db;
          }
          .gptp-settings-row input[type="number"] {
            width: 120px;
          }
          .gptp-settings-description {
            margin-top: 0.5rem;
            font-size: 0.9rem;
            color: #808080;
          }
          .gptp-settings-save {
            margin-top: 1rem;
            padding: 0.8rem 1.5rem;
            background: #3498db;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            transition: background 0.2s;
          }
          .gptp-settings-save:hover {
            background: #2980b9;
          }
        </style>
        <div class="gptp-settings">
          <div class="gptp-settings-group">
            <h3>通用 API 设置</h3>
            <div class="gptp-settings-row">
              <label>OpenAI API Key</label>
              <input type="password" id="gptp_openai_api_key" value="${opts.gptp_openai_api_key || ''}">
              <div class="gptp-settings-description">用于访问 OpenAI API 的密钥</div>
            </div>
            <div class="gptp-settings-row">
              <label>DeepSeek API Key</label>
              <input type="password" id="gptp_deepseek_api_key" value="${opts.gptp_deepseek_api_key || ''}">
              <div class="gptp-settings-description">用于访问 DeepSeek API 的密钥</div>
            </div>
            <div class="gptp-settings-row">
              <label>SiliconFlow API Key</label>
              <input type="password" id="gptp_siliconflow_api_key" value="${opts.gptp_siliconflow_api_key || ''}">
              <div class="gptp-settings-description">用于访问 SiliconFlow API 的密钥</div>
            </div>
          </div>

          <div class="gptp-settings-group">
            <h3>腾讯混元设置</h3>
            <div class="gptp-settings-row">
              <label>API Key (兼容模式)</label>
              <input type="password" id="gptp_hunyuan_api_key" value="${opts.gptp_hunyuan_api_key || ''}">
              <div class="gptp-settings-description">用于兼容模式的 API Key</div>
            </div>
            <div class="gptp-settings-row">
              <label>Secret ID (签名模式)</label>
              <input type="password" id="gptp_hunyuan_secret_id" value="${opts.gptp_hunyuan_secret_id || ''}">
              <div class="gptp-settings-description">密钥 ID</div>
            </div>
            <div class="gptp-settings-row">
              <label>Secret Key (签名模式)</label>
              <input type="password" id="gptp_hunyuan_secret_key" value="${opts.gptp_hunyuan_secret_key || ''}">
              <div class="gptp-settings-description">密钥内容</div>
            </div>
          </div>

          <div class="gptp-settings-group">
            <h3>火山方舟设置</h3>
            <div class="gptp-settings-row">
              <label>API Key (兼容模式)</label>
              <input type="password" id="gptp_volcengine_ark_api_key" value="${opts.gptp_volcengine_ark_api_key || ''}">
              <div class="gptp-settings-description">用于兼容模式的 API Key</div>
            </div>
            <div class="gptp-settings-row">
              <label>Access Key (签名模式)</label>
              <input type="password" id="gptp_volcengine_ark_ak" value="${opts.gptp_volcengine_ark_ak || ''}">
              <div class="gptp-settings-description">访问密钥 ID (AK)</div>
            </div>
            <div class="gptp-settings-row">
              <label>Secret Key (签名模式)</label>
              <input type="password" id="gptp_volcengine_ark_sk" value="${opts.gptp_volcengine_ark_sk || ''}">
              <div class="gptp-settings-description">访问密钥内容 (SK)</div>
            </div>
          </div>

          <div class="gptp-settings-group">
            <h3>百度千帆设置</h3>
            <div class="gptp-settings-row">
              <label>API Key (兼容模式)</label>
              <input type="password" id="gptp_baidu_qianfan_api_key" value="${opts.gptp_baidu_qianfan_api_key || ''}">
              <div class="gptp-settings-description">用于兼容模式的 API Key</div>
            </div>
            <div class="gptp-settings-row">
              <label>API Key (签名模式)</label>
              <input type="password" id="gptp_baidu_qianfan_api_key_native" value="${opts.gptp_baidu_qianfan_api_key || ''}">
              <div class="gptp-settings-description">API Key</div>
            </div>
            <div class="gptp-settings-row">
              <label>Secret Key (签名模式)</label>
              <input type="password" id="gptp_baidu_qianfan_secret_key" value="${opts.gptp_baidu_qianfan_secret_key || ''}">
              <div class="gptp-settings-description">Secret Key</div>
            </div>
          </div>

          <div class="gptp-settings-group">
            <h3>其他设置</h3>
            <div class="gptp-settings-row">
              <label>最大图片大小 (MB)</label>
              <input type="number" id="gptp_hunyuan_max_image_size" value="${opts.gptp_hunyuan_max_image_size || 5}" min="1" max="20">
              <div class="gptp-settings-description">上传图片的最大大小限制</div>
            </div>
          </div>
        </div>
      `,
      buttons: [
        {
          text: '保存',
          action: function() {
            // 保存所有设置
            const settings = {
              gptp_openai_api_key: document.getElementById('gptp_openai_api_key').value,
              gptp_deepseek_api_key: document.getElementById('gptp_deepseek_api_key').value,
              gptp_siliconflow_api_key: document.getElementById('gptp_siliconflow_api_key').value,
              gptp_hunyuan_api_key: document.getElementById('gptp_hunyuan_api_key').value,
              gptp_hunyuan_secret_id: document.getElementById('gptp_hunyuan_secret_id').value,
              gptp_hunyuan_secret_key: document.getElementById('gptp_hunyuan_secret_key').value,
              gptp_volcengine_ark_api_key: document.getElementById('gptp_volcengine_ark_api_key').value,
              gptp_volcengine_ark_ak: document.getElementById('gptp_volcengine_ark_ak').value,
              gptp_volcengine_ark_sk: document.getElementById('gptp_volcengine_ark_sk').value,
              gptp_baidu_qianfan_api_key: document.getElementById('gptp_baidu_qianfan_api_key').value,
              gptp_baidu_qianfan_api_key_native: document.getElementById('gptp_baidu_qianfan_api_key_native').value,
              gptp_baidu_qianfan_secret_key: document.getElementById('gptp_baidu_qianfan_secret_key').value,
              gptp_hunyuan_max_image_size: document.getElementById('gptp_hunyuan_max_image_size').value
            };

            // 保存到 opts 对象
            Object.assign(opts, settings);

            // 保存到本地存储
            Object.entries(settings).forEach(([key, value]) => {
              if (value) {
                localStorage.setItem(key, value);
              } else {
                localStorage.removeItem(key);
              }
            });

            gptp.toastr.success('设置已保存');
            gptp.dialog.hide();
          },
          className: 'gptp-settings-save'
        },
        {
          text: '取消'
        }
      ]
    });
  }

  return {
    init: init,
    applyPrompt: applyPrompt,
    loadUI: loadUI,
    showTagManager: showTagManager,
    selectTag: selectTag,
    deleteTag: deleteTag,
    addNewTag: addNewTag,
    removeUploadedImage: function (event) {
      event.stopPropagation();
      event.preventDefault();
      const previewContainer = event.target.closest('.gptp-preview-container');
      if (previewContainer) previewContainer.remove();
      const imageInput = document.getElementById('gptp-image-input');
      if (imageInput) {
        imageInput.value = '';
        imageInput.dispatchEvent(new Event('change'));
      }
      delete gptp.core.currentImageFile;
    }
  };
})();

(function () {
  const init = () => {
    if (window.gptp?.core && !window._gptp_initialized) {
      window._gptp_initialized = true;
      gptp.core.init();
    }
  };

  if (document.readyState === 'complete') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
    window.addEventListener('load', init);
  }
})();

gptp.core.handleImageUpload = function (e) {
  const file = e.target.files[0];
  if (!file) return;
  if (!file.type.match(/image\/(jpeg|png|webp)/)) {
    gptp.toastr.error('仅支持JPEG/PNG/WEBP格式');
    e.target.value = '';
    return;
  }
  const maxSize = (opts.gptp_hunyuan_max_image_size || 5) * 1024 * 1024;
  if (file.size > maxSize) {
    gptp.toastr.error(`图片大小不能超过${opts.gptp_hunyuan_max_image_size}MB`);
    e.target.value = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = (event) => {
    document.getElementById('gptp-media-preview').innerHTML = `
      <div class="gptp-preview-container">
        <img src="${event.target.result}" class="gptp-preview-image">
        <div class="gptp-preview-meta">
          ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)
          <button class="gptp-delete-btn gptp-image-delete-btn" onclick="gptp.core.removeUploadedImage(event)">×</button>
        </div>
      </div>
    `;
  };
  reader.readAsDataURL(file);
};

document.addEventListener('DOMContentLoaded', () => {
  const imageInput = document.getElementById('gptp-image-input');
  if (imageInput) {
    imageInput.addEventListener('change', gptp.core.handleImageUpload);
  }
});