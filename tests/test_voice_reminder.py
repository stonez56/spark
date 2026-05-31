import sys
import os

# Append workspace path to system paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brain import OllamaBrain

def test():
    print("=== Testing OllamaBrain Reminder Intent & Extraction ===")
    brain = OllamaBrain()
    
    # Test cases for intent routing
    test_phrases = [
        "提醒我下午吃藥",
        "幫我記住買雞蛋",
        "叫我起床",
        "4點半叫我吃藥",
        "體型我要買雞蛋",  # ASR homophone matching
        "今天集合集號",    # datetime classification fallback
        "我們集合提醒我買雞蛋", # complex sentence
        "我要吃藥",  # should fall into health_query
        "我上次就提醒過你, 不要忘了吃藥, 你怎麼又忘了",  # should fall into chat (bypassing rules)
        "謝謝你的提醒"  # should fall into chat (bypassing rules)
    ]
    
    print("\n1. Testing Intent Routing:")
    for phrase in test_phrases:
        action = brain.route_intent(phrase)
        print(f"Phrase: '{phrase}' ➔ Action: '{action}'")
        
    # Test cases for parameter extraction
    extraction_phrases = [
        "提醒我一下,4.50分我要吃藥",
        "幫我記一下買雞蛋",
        "下午五點",
        "提醒我買衛生紙",
        "在家裡,明天早上7點"
    ]
    
    print("\n2. Testing Parameter Extraction:")
    for phrase in extraction_phrases:
        parsed = brain.parse_reminder_data(phrase)
        print(f"Phrase: '{phrase}' ➔ Parsed: {parsed}")

    # Test trailing '4' / '４' whisper hallucination cleanup
    print("\n3. Testing ASR Trailing '4' / '４' Filter:")
    import re
    def filter_trailing_noise(text):
        return re.sub(r'(?<!\d)(?<![一二三四五六七八九十百分點時日月年])([4４])$', '', text.strip()).strip()
    
    test_asr_outputs = [
        "今天幾月幾號４",
        "我們集合提醒我買雞蛋 4",
        "下午4點",
        "24",
        "今天5月31號４"
    ]
    for out in test_asr_outputs:
        filtered = filter_trailing_noise(out)
        print(f"Raw: '{out}' ➔ Filtered: '{filtered}'")

    # Test Chinese Confirmation Formatter
    print("\n4. Testing Chinese Confirmation Formatter:")
    from main import format_reminder_confirmation
    confirmations_to_test = [
        ("吃藥", "16:50", "2026-05-31"),
        ("買雞蛋", "17:00", "2026-05-31"),
        ("買衛生紙", "07:00", "2026-06-01"),
        ("起床", "07:30", "2026-06-01"),
        ("散步", "02:20", "2026-06-02")
    ]
    for msg, t, d in confirmations_to_test:
        formatted = format_reminder_confirmation(msg, t, d)
        print(f"Params: msg='{msg}', time='{t}', date='{d}' ➔ Confirmation: '{formatted}'")

    # Test Reminder Trigger Sentence Generator
    print("\n4.5. Testing Reminder Trigger Sentence Formatter:")
    from main import format_reminder_trigger_sentence
    trigger_messages = ["吃藥", "買衛生紙", "買雞蛋", "起床"]
    for msg in trigger_messages:
        sentence = format_reminder_trigger_sentence(msg)
        print(f"Trigger Message: '{msg}' ➔ Synthesized Sentence: '{sentence}'")

    # Test TTS translation of numbers and times
    print("\n5. Testing TTS Translation:")
    from tts import SparkTTS
    tts_model = SparkTTS()
    test_texts = [
        "記下來了！今天下午 07:00 提醒你 買衛生紙 喵！",
        "記下來了！明天早上 07:30 提醒你 起床 喵！",
        "記下來了！今天下午 16:50 提醒你 吃藥 喵！",
        "好的，設定在後天半夜 02:20 提醒你 散步 喵！"
    ]
    for text in test_texts:
        spoken = tts_model._convert_numbers_to_zh(text)
        print(f"Raw TTS: '{text}' ➔ Spoken TTS: '{spoken}'")

    # Test JS Weekday Mapping
    print("\n6. Testing JS Weekday Mapping:")
    from main import get_js_weekday
    dates_to_test = [
        "2026-05-31",  # Sunday -> expected '0'
        "2026-06-01",  # Monday -> expected '1'
        "2026-06-06",  # Saturday -> expected '6'
        None
    ]
    for d in dates_to_test:
        wk = get_js_weekday(d) if d else "0,1,2,3,4,5,6"
        print(f"Date: '{d}' ➔ JS Weekday Index: '{wk}'")

    # Test 7: Database one-off days_of_week override verification
    print("\n7. Testing Database One-Off days_of_week Override:")
    import reminders_db
    # Clear old test reminders if any
    all_rems = reminders_db.get_all_reminders()
    for r in all_rems:
        if r['message'] == "測試吃藥單次":
            reminders_db.delete_reminder(r['id'])
            
    # Add a single-day reminder with start_date == end_date == "2026-05-31" (Sunday)
    # Even if we pass days_of_week="0,1,2,3,4,5,6", the database should override it to "0" (Sunday)
    reminders_db.add_reminder(
        message="測試吃藥單次",
        times="22:30",
        days_of_week="0,1,2,3,4,5,6",
        start_date="2026-05-31",
        end_date="2026-05-31"
    )
    
    # Retrieve and check
    rems = reminders_db.get_all_reminders()
    added_rem = next((r for r in rems if r['message'] == "測試吃藥單次"), None)
    if added_rem:
        print(f"Inserted single-day reminder days_of_week: '{added_rem['days_of_week']}' (Expected: '0')")
        # Cleanup
        reminders_db.delete_reminder(added_rem['id'])
    else:
        print("Failed to find inserted test reminder.")

if __name__ == "__main__":
    test()
