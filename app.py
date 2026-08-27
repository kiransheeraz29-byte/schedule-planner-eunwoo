from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime
import random
import re
import json
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
app = Flask(__name__)

# Get API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"✅ API Key loaded: {GEMINI_API_KEY[:10]}...")

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini configured successfully!")
except Exception as e:
    print(f"❌ Failed to configure Gemini: {e}")

# Initialize model
model = None
model_names = [
    'gemini-1.5-flash',
    'gemini-1.5-pro', 
    'gemini-pro',
    'models/gemini-1.5-flash',
    'models/gemini-1.5-pro',
]

for model_name in model_names:
    try:
        print(f"🔄 Trying: {model_name}")
        test_model = genai.GenerativeModel(model_name)
        test_response = test_model.generate_content("Say OK")
        if test_response and test_response.text:
            model = test_model
            print(f"✅ Using model: {model_name}")
            break
    except Exception as e:
        print(f"❌ {model_name} failed: {str(e)[:80]}")
        continue

# ============================================
# GREY COLOR PALETTES
# ============================================
COLOR_PALETTES = [
    {'primary': '#4A4A4A', 'secondary': '#2A2A2A', 'accent': '#6B6B6B', 'bg': '#1A1A1A', 'card': '#2D2D2D', 'text': '#E8E8E8'},
    {'primary': '#5A5A5A', 'secondary': '#333333', 'accent': '#777777', 'bg': '#222222', 'card': '#3A3A3A', 'text': '#F0F0F0'},
    {'primary': '#3D3D3D', 'secondary': '#1E1E1E', 'accent': '#5E5E5E', 'bg': '#141414', 'card': '#282828', 'text': '#E0E0E0'},
    {'primary': '#6A6A6A', 'secondary': '#404040', 'accent': '#888888', 'bg': '#2A2A2A', 'card': '#4A4A4A', 'text': '#F5F5F5'},
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def extract_schedule_details(prompt):
    """Extract days and time slots from prompt"""
    days = 7
    time_slots = ['8:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00']
    
    # Extract number of days
    day_match = re.search(r'(\d+)\s*(?:day|days?)', prompt.lower())
    if day_match:
        days = int(day_match.group(1))
        days = max(1, min(days, 14))
    
    # Extract hours per day
    hour_match = re.search(r'(\d+)\s*(?:hours?|hrs?)\s*(?:per\s*day)?', prompt.lower())
    if hour_match:
        hours_per_day = int(hour_match.group(1))
        hours_per_day = min(hours_per_day, 12)
        time_slots = []
        for h in range(8, min(8 + hours_per_day * 2, 22), 2):
            ampm = "AM" if h < 12 else "PM"
            display_hour = h if h <= 12 else h - 12
            time_slots.append(f"{display_hour}:00 {ampm}")
    
    # Extract time range
    time_match = re.search(r'from\s*(\d+)\s*(?:am|pm|AM|PM)\s*to\s*(\d+)\s*(?:am|pm|AM|PM)', prompt.lower())
    if time_match:
        start = int(time_match.group(1))
        end = int(time_match.group(2))
        if start < end and end - start <= 12:
            time_slots = []
            for h in range(start, end + 1, 2):
                ampm = "AM" if h < 12 else "PM"
                display_hour = h if h <= 12 else h - 12
                time_slots.append(f"{display_hour}:00 {ampm}")
    
    return days, time_slots

def generate_schedule_with_gemini(prompt, days, time_slots):
    """Generate a schedule using Gemini or fallback"""
    if model:
        try:
            schedule_prompt = f"""
Based on this request: "{prompt}"
Create a schedule with {days} days and these time slots: {', '.join(time_slots)}

Return ONLY a JSON object with this exact format:
{{
    "title": "Schedule Title",
    "days": ["Day1", "Day2", ...],
    "activities": {{
        "Day1": ["Activity for time 1", "Activity for time 2", ...],
        "Day2": ["Activity for time 1", "Activity for time 2", ...]
    }}
}}
Each activity should be specific to the request (4-6 words max).
Make it practical and detailed.
"""
            response = model.generate_content(schedule_prompt)
            if response and response.text:
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    schedule_data = json.loads(json_match.group())
                    return schedule_data
        except Exception as e:
            print(f"⚠️ Gemini schedule error: {e}")
    
    # Fallback schedule generation
    return generate_fallback_schedule(prompt, days, time_slots)

def generate_fallback_schedule(prompt, days, time_slots):
    """Generate a detailed fallback schedule"""
    fallback_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][:days]
    
    # Detect topic
    prompt_lower = prompt.lower()
    
    # Activity sets for different topics
    if any(word in prompt_lower for word in ['math', 'mathematics', 'algebra', 'calculus']):
        activities = ['Algebra Practice', 'Geometry Review', 'Calculus Problems', 'Statistics', 'Trigonometry', 'Math Theory', 'Problem Solving']
        title = "📐 MATH STUDY PLAN"
    elif any(word in prompt_lower for word in ['science', 'physics', 'chemistry', 'biology']):
        activities = ['Physics Theory', 'Chemistry Lab', 'Biology Review', 'Scientific Method', 'Experiment Design', 'Data Analysis', 'Research']
        title = "🔬 SCIENCE SCHEDULE"
    elif any(word in prompt_lower for word in ['work', 'job', 'office', 'professional']):
        activities = ['Morning Meetings', 'Deep Work Session', 'Task Management', 'Project Review', 'Team Collaboration', 'Planning', 'Documentation']
        title = "💼 WORK SCHEDULE"
    elif any(word in prompt_lower for word in ['exam', 'test', 'quiz', 'final']):
        activities = ['Topic Revision', 'Practice Questions', 'Mock Test', 'Review Mistakes', 'Flashcards', 'Summary Notes', 'Rest']
        title = "📝 EXAM PREPARATION"
    elif any(word in prompt_lower for word in ['gym', 'workout', 'fitness', 'exercise']):
        activities = ['Cardio Session', 'Strength Training', 'Core Workout', 'Stretching', 'HIIT', 'Yoga', 'Recovery']
        title = "💪 FITNESS PLAN"
    elif any(word in prompt_lower for word in ['coding', 'programming', 'developer', 'software']):
        activities = ['Code Practice', 'Debug Session', 'Project Work', 'Learning New Tech', 'Code Review', 'Documentation', 'Testing']
        title = "💻 CODING SCHEDULE"
    else:
        activities = ['Focus Session', 'Task Completion', 'Review & Planning', 'Learning', 'Practice', 'Reflection', 'Rest']
        title = "📅 DAILY SCHEDULE"
    
    # Distribute activities across days and time slots
    activities_by_day = {}
    for i, day in enumerate(fallback_days):
        day_activities = []
        for j in range(len(time_slots)):
            # Mix up activities for variety
            activity_idx = (i * 2 + j) % len(activities)
            if i % 2 == 0 and j % 2 == 0:
                day_activities.append(f"{activities[activity_idx]} (Deep Focus)")
            elif i % 2 == 1 and j % 2 == 1:
                day_activities.append(f"{activities[activity_idx]} (Review)")
            else:
                day_activities.append(activities[activity_idx])
        activities_by_day[day] = day_activities
    
    return {
        "title": title,
        "days": fallback_days,
        "activities": activities_by_day
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'response': 'Please enter a message.'})
        
        # Check if it's a schedule request
        is_schedule_request = any(word in user_message.lower() for word in ['plan', 'schedule', 'planner', 'make', 'create', 'generate'])
        
        if is_schedule_request:
            # Extract details and generate schedule
            days, time_slots = extract_schedule_details(user_message)
            schedule_data = generate_schedule_with_gemini(user_message, days, time_slots)
            
            # Format the response
            response_text = f"📅 **{schedule_data['title']}**\n\n"
            response_text += f"📆 {days} days • {len(time_slots)} time slots\n\n"
            
            for day in schedule_data['days']:
                response_text += f"**{day}**\n"
                activities = schedule_data['activities'].get(day, [])
                for i, activity in enumerate(activities):
                    if i < len(time_slots):
                        response_text += f"  • {time_slots[i]} - {activity}\n"
                response_text += "\n"
            
            response_text += "\n💡 **Tips:**\n"
            response_text += "• Take a 5-10 min break every hour\n"
            response_text += "• Stay hydrated and stretch regularly\n"
            response_text += "• Review your progress at the end of each day\n\n"
            response_text += "🎨 I can also generate a visual image of this schedule! Say 'Generate schedule image' or click the image button."
            
            return jsonify({'response': response_text})
        
        # For non-schedule requests, use Gemini or fallback
        if model:
            try:
                response = model.generate_content(f"""
You are Eunwoo, a helpful schedule planning assistant.
Give brief, practical responses. Use emojis.
User: {user_message}
Eunwoo:""")
                if response and response.text:
                    return jsonify({'response': response.text})
            except:
                pass
        
        # Fallback responses
        fallback = [
            "I can help you create schedules! Try saying:\n• 'Plan 4 hours study'\n• '3 days work schedule'\n• 'Generate a schedule image'",
            "Let me help you plan! Tell me what you want to schedule and for how many hours or days.",
            "I'm here to organize your time! What would you like to plan today?"
        ]
        return jsonify({'response': random.choice(fallback)})
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({'response': "Let me help you plan! Try: 'Plan 4 hours study' or '3 days work schedule'"})

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        prompt = data.get('prompt', 'Create a weekly schedule')
        
        # Extract schedule details
        days, time_slots = extract_schedule_details(prompt)
        
        # Generate schedule data
        schedule_data = generate_schedule_with_gemini(prompt, days, time_slots)
        
        days_list = schedule_data.get('days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'][:days])
        activities_by_day = schedule_data.get('activities', {})
        
        # Ensure activities match days
        if not activities_by_day or len(activities_by_day) != len(days_list):
            activities_by_day = {}
            for day in days_list:
                activities_by_day[day] = [f"Activity {i+1}" for i in range(len(time_slots))]
        
        palette = random.choice(COLOR_PALETTES)
        
        margin = 30
        header_height = 75
        row_height = 55
        time_col_width = 70
        cell_width = 140 if days <= 5 else 110
        
        width = margin * 2 + time_col_width + (cell_width * days) + 20
        height = header_height + 40 + (row_height * len(time_slots)) + 50
        width = max(width, 700)
        height = max(height, 500)
        
        img = Image.new('RGB', (width, height), color=palette['bg'])
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("arial.ttf", 26)
            font_subtitle = ImageFont.truetype("arial.ttf", 14)
            font_header = ImageFont.truetype("arial.ttf", 15)
            font_text = ImageFont.truetype("arial.ttf", 12)
            font_time = ImageFont.truetype("arial.ttf", 14)
            font_footer = ImageFont.truetype("arial.ttf", 12)
        except:
            font_title = font_subtitle = font_header = font_text = font_time = font_footer = ImageFont.load_default()
        
        # Header gradient
        for i in range(header_height):
            ratio = i / header_height
            r1, g1, b1 = hex_to_rgb(palette['primary'])
            r2, g2, b2 = hex_to_rgb(palette['accent'])
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.rectangle([0, i, width, i+1], fill=(r, g, b))
        
        title = f"📅 EUNWOO SCHEDULE"
        if days == 1:
            title += " (1 Day)"
        elif days <= 5:
            title += f" ({days} Days)"
        
        draw.text((margin + 10, 10), title, fill='#FFFFFF', font=font_title)
        subtitle = prompt[:55] + '...' if len(prompt) > 55 else prompt
        draw.text((margin + 10, 45), f"📌 {subtitle}", fill='#FFFFFF', font=font_subtitle)
        
        y_start = header_height + 20
        
        # Day headers
        for i, day in enumerate(days_list):
            x = margin + time_col_width + i * cell_width
            draw.rectangle([x, y_start, x + cell_width, y_start + 35], fill=palette['primary'])
            display_day = day[:4] if days > 5 else day[:6]
            text_width = draw.textlength(display_day, font=font_header)
            text_x = x + (cell_width - text_width) // 2
            draw.text((text_x, y_start + 8), display_day, fill='#FFFFFF', font=font_header)
        
        y = y_start + 35
        emojis = ['📚', '✏️', '📖', '💡', '🎯', '⭐', '🔥', '💪', '🧘', '🎨', '💻', '📝']
        
        # Table rows
        for time_idx, time in enumerate(time_slots):
            if time_idx % 2 == 0:
                draw.rectangle([margin, y, width - margin, y + row_height], fill=palette['card'])
            else:
                draw.rectangle([margin, y, width - margin, y + row_height], fill=palette['bg'])
            
            # Time column
            draw.rectangle([margin, y, margin + time_col_width, y + row_height], fill=palette['secondary'])
            text_width = draw.textlength(time, font=font_time)
            text_x = margin + (time_col_width - text_width) // 2
            draw.text((text_x, y + 18), time, fill=palette['text'], font=font_time)
            
            # Activities
            for day_idx in range(days):
                x = margin + time_col_width + day_idx * cell_width
                day_name = days_list[day_idx]
                day_activities = activities_by_day.get(day_name, [])
                activity = day_activities[time_idx] if time_idx < len(day_activities) else "Break"
                
                if activity and activity != "Break":
                    emoji = random.choice(emojis)
                    dot_color = random.choice([palette['primary'], palette['accent']])
                    dot_x = x + 6
                    dot_y = y + 20
                    draw.ellipse([dot_x, dot_y, dot_x + 8, dot_y + 8], fill=dot_color)
                    
                    display_text = f"{emoji} {activity[:12]}"
                    if len(activity) > 12:
                        display_text = f"{emoji} {activity[:10]}.."
                    
                    text_x = x + 18
                    text_y = y + 17
                    draw.text((text_x, text_y), display_text, fill=palette['text'], font=font_text)
                else:
                    dot_x = x + 10
                    dot_y = y + 24
                    draw.ellipse([dot_x, dot_y, dot_x + 5, dot_y + 5], fill='#4A4A4A')
            
            y += row_height
        
        # Grid lines
        for i in range(days + 1):
            x = margin + time_col_width + i * cell_width
            draw.line([x, y_start + 35, x, y], fill='#4A4A4A', width=1)
        
        y_line = y_start + 35
        for i in range(len(time_slots) + 1):
            draw.line([margin, y_line, width - margin, y_line], fill='#4A4A4A', width=1)
            y_line += row_height
        
        # Footer
        footer_y = height - 30
        quotes = ["✨ Stay consistent, stay focused", "📚 Small steps lead to big results", "💪 You've got this!", "🌟 Make every day count"]
        draw.text((margin + 10, footer_y), random.choice(quotes), fill=palette['text'], font=font_footer)
        
        brand_text = f"📅 Eunwoo Planner ({days} days)"
        brand_width = draw.textlength(brand_text, font=font_footer)
        draw.text((width - margin - brand_width - 10, footer_y), brand_text, fill=palette['text'], font=font_footer)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f'planner_{timestamp}.png'
        image_path = os.path.join('static', filename)
        
        os.makedirs('static', exist_ok=True)
        img.save(image_path, quality=95)
        
        return jsonify({
            'image_url': f'/{image_path}',
            'success': True,
            'days': days,
            'time_slots': len(time_slots),
            'schedule': schedule_data
        })
        
    except Exception as e:
        print(f"❌ Image Generation Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
        






