# Breeze Model for Pi5 

**For a Pi5 chatbot project in Taiwan, MediaTek’s Breeze models are a strong choice if your goal is *local language accuracy and cultural fit*. Breeze 3 adds 台語 (Taiwanese Hokkien) speech recognition and synthesis, plus a content safety model tuned for Taiwan’s social context. On Pi5 with NVMe SSD + cooling, the smaller Breeze ASR/TTS models are practical, while the larger Breeze LLMs (3B–8B) may run but with slower speeds.**  

---

## 🌬️ Breeze Model Highlights (MTK Research)

| Model | Purpose | Key Features | Suitability for Pi5 |
|-------|----------|--------------|---------------------|
| **Breeze ASR 25/26** | Speech recognition | Built on Whisper, trained with 10,000+ hours of Taiwanese Mandarin + 台語 synthetic speech; handles code-switching (Mandarin + English + 台語) with **+10% accuracy vs Whisper** and **+56% better code-switching**  [MediaTek](https://www.mediatek.com/zh-tw/press-room/mediatek-research-unveils-mr-breeze-asr-25-an-open-source-ai-model-for-taiwanese-speech) | ✅ Lightweight, runs well on Pi5; ideal for chatbot voice input |
| **BreezyVoice 26** | Speech synthesis | CosyVoice2-based, generates natural 台語 speech with MOS 5/5 quality; supports Mandarin + 台語 output  [MediaTek](https://www.mediatek.com/zh-tw/tek-talk-blogs/mediatek-research-breeze-3) | ✅ Usable on Pi5; NVMe helps streaming longer outputs |
| **Breeze Guard 26** | Content safety | Trained on 12,000+ Taiwan-specific harmful content cases (詐騙, 不雅言語, 政治操弄); filters unsafe chatbot replies  [MediaTek](https://www.mediatek.com/zh-tw/tek-talk-blogs/mediatek-research-breeze-3) | ✅ Lightweight classifier, good for classroom demos |
| **Breeze 2 LLM (3B/8B)** | Language + multimodal | Based on LLaMA 3.2, enhanced for Traditional Chinese; supports vision input + function calling  [Github](https://github.com/mtkresearch/MR-Models) | ⚠️ 3B Q4 may run (~8–12 tok/s); 8B too heavy for Pi5 |

---

## 📊 Comparison: Breeze vs. Qwen on Pi5

| Aspect | **Breeze (MTK)** | **Qwen (Alibaba)** |
|--------|------------------|--------------------|
| **Language fit** | Optimized for 繁體中文 + 台語; culturally tuned | Strong Mandarin + English; less 台語 |
| **Speech support** | Native ASR + TTS (台語 + Mandarin) | No built-in speech; needs Whisper/Piper |
| **Safety** | Taiwan-specific harmful content guard | General safety, less local |
| **Performance on Pi5** | ASR/TTS lightweight; 3B LLM borderline usable | 1.8B–3B MOE runs faster (~12–15 tok/s) |
| **Community support** | MTK Research GitHub, Taiwan-focused | Global HuggingFace + open-source |

---

## 🎯 Recommendation for Your Chatbot
- **If your chatbot is Taiwan-facing (students, local users, 台語/繁中)** → **Breeze ASR + BreezyVoice + Breeze Guard** are excellent. Pair with a small LLM (Breeze 2 3B Q4 or Qwen2.5-1.8B Q4) for text reasoning.  
- **If you prioritize speed and reasoning depth** → Qwen MOE small models outperform Breeze LLMs on Pi5.  
- **Hybrid approach**:  
  - Use **Breeze ASR/TTS** for speech I/O.  
  - Use **Qwen2.5-1.8B Q4** for text reasoning.  
  - Add **Breeze Guard** for Taiwan-specific safety.  

---

✅ Bottom line: **On Pi5 with NVMe SSD + cooling, Breeze is unbeatable for Taiwan-local speech and safety, while Qwen is better for fast reasoning.** Combine them for the best classroom chatbot experience.  


# Llama.cpp adptation

## Llama speed up tutorial on 6GB Nvidia card
- Can't be used with a Pi5 because Pi5 doesn't have a GPU
- https://www.youtube.com/watch?v=8F_5pdcD3HY&t=2s



---

## ⚡ Why Llama.cpp is Better on Pi5
- **Lean & Efficient**: Llama.cpp is a lightweight C++ engine with minimal overhead. On Pi5 (8GB RAM), every MB counts, and Llama.cpp avoids the extra memory footprint of Ollama’s Go server layer.
- **Speed**: Benchmarks show ~10–20% faster token throughput on Pi5 with quantized 2–3B models (e.g., Gemma2:2B Q4, Phi-3.5 mini Q4). That difference is noticeable when you’re already limited to ~10–15 tok/s.
- **Flexibility**: You can fine‑tune context window, quantization level, and threading directly. Ollama abstracts these settings, which is easier but less controllable.
- **Lower Latency for First Token**: While Ollama shines with caching, Pi5 doesn’t benefit much because you’re not running multiple concurrent sessions. Llama.cpp’s raw efficiency matters more.

---
---

## ✅ Practical Recommendation
- For your **Cat Chatbot robot on Pi5**:  
  → **Use Llama.cpp** with small quantized models (Gemma2:2B Q4, Phi-3.5 mini Q4).  
  → Pair with **Whisper small** for speech input and **Piper TTS** for voice output.  
  → Keep context window modest (8k–16k) to avoid RAM exhaustion.  
  → Add active cooling + NVMe SSD for stability.  


---
