import logging
import uuid
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7922484259:AAH21mVqLF0OAeughkVXXrJ3_zOzuyJICys')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '1751803948,6392794694').split(',')]
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@G_king123f')
BTC_WALLET = os.getenv('BTC_WALLET', '8yt1x4XqPJqgdS95M8nrDpczkzyoYr4oGL8NDjEqXASj')

# Social media links
TELEGRAM_COMMUNITY = "https://t.me/Heartbotai"
X_ACCOUNT = "https://x.com/gtaddala/status/1932420174499516555?t=b-dPk3teB14KmwEY_MWWhA&s=19"

# Global data storage
teachers = []
bookings = []
pending_payments = {}
user_states = {}
teacher_edit_states = {}

# New data structures for referral and points system
user_referrals = {}  # {user_id: {'referral_code': 'ABC123', 'referred_by': user_id, 'referrals': [user_ids], 'points': 0}}
point_transfers = []  # Transaction history for point transfers
teacher_point_prices = {}  # {teacher_id: point_price} - admin can set point pricing

# Teacher management conversation states
TEACHER_EDIT_STATES = {
    'WAITING_FOR_FIELD': 'waiting_for_field',
    'WAITING_FOR_VALUE': 'waiting_for_value',
    'WAITING_FOR_NEW_TEACHER': 'waiting_for_new_teacher',
    'WAITING_FOR_POINT_PRICE': 'waiting_for_point_price',
    'WAITING_FOR_TRANSFER_USER': 'waiting_for_transfer_user',
    'WAITING_FOR_TRANSFER_AMOUNT': 'waiting_for_transfer_amount'
}

# Initialize sample teacher data
def initialize_teachers():
    global teachers
    teachers = [
        {
            'id': 1,
            'name': 'Sarah Johnson',
            'age': 28,
            'subjects': ['Mathematics', 'Physics'],
            'price': 25,
            'photo': 'https://images.unsplash.com/photo-1494790108755-2616c78746d5?w=400&h=400&fit=crop&crop=face',
            'available': True,
            'bio': 'Expert mathematician with 5+ years teaching experience. Specializes in making complex concepts simple and engaging.',
            'education': 'MSc Mathematics, Stanford University',
            'experience': '2+ years of webcam worker',
            'rating': 4.9,
            'why_choose': 'i love working on webcam i can make you happy.'
        },
        {
            'id': 2,
            'name': 'Michael Chen',
            'age': 35,
            'subjects': ['Computer Science', 'Programming'],
            'price': 30,
            'photo': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face',
            'available': True,
            'bio': 'Senior software engineer turned educator. Passionate about teaching modern programming and software development.',
            'education': 'PhD Computer Science, MIT',
            'experience': '8+ years industry + 3 years teaching',
            'rating': 4.8,
            'why_choose': 'i do with so many styels ass, footjob, fisting and etc book me love.'
        },
        {
            'id': 3,
            'name': 'Emily Rodriguez',
            'age': 26,
            'subjects': ['English', 'Literature'],
            'price': 20,
            'photo': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop&crop=face',
            'available': True,
            'bio': 'Native English speaker with expertise in literature and creative writing. Makes learning fun and interactive.',
            'education': 'MA English Literature, Oxford University',
            'experience': '4+ years teaching experience',
            'rating': 4.7,
            'why_choose': 'I create engaging lessons that improve both your language skills and confidence.'
        },
        {
            'id': 4,
            'name': 'Sophia Martinez',
            'age': 24,
            'subjects': ['Spanish', 'Dance'],
            'price': 22,
            'photo': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop&crop=face',
            'available': True,
            'bio': 'Passionate Spanish teacher and dancer. Brings energy and culture to every session.',
            'education': 'BA Spanish Literature, Barcelona University',
            'experience': '3+ years teaching experience',
            'rating': 4.6,
            'why_choose': 'I bring passion and energy to make learning enjoyable and memorable.'
        },
    ]
    logger.info(f"Initialized {len(teachers)} teachers")

# Referral system functions
def generate_referral_code():
    """Generate a unique 6-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def initialize_user_referral(user_id, referred_by=None):
    """Initialize referral data for a new user"""
    if user_id not in user_referrals:
        referral_code = generate_referral_code()
        # Ensure unique referral code
        while any(data['referral_code'] == referral_code for data in user_referrals.values()):
            referral_code = generate_referral_code()
        
        user_referrals[user_id] = {
            'referral_code': referral_code,
            'referred_by': referred_by,
            'referrals': [],
            'points': 0,
            'total_earned': 0
        }
        
        # Award point to referrer if applicable
        if referred_by and referred_by in user_referrals:
            user_referrals[referred_by]['referrals'].append(user_id)
            user_referrals[referred_by]['points'] += 1
            user_referrals[referred_by]['total_earned'] += 1
            logger.info(f"User {referred_by} earned 1 point for referring user {user_id}")

def get_user_by_referral_code(referral_code):
    """Find user ID by referral code"""
    for user_id, data in user_referrals.items():
        if data['referral_code'] == referral_code:
            return user_id
    return None

def transfer_points(from_user_id, to_user_id, amount):
    """Transfer points between users"""
    if from_user_id not in user_referrals or to_user_id not in user_referrals:
        return False, "User not found"
    
    if user_referrals[from_user_id]['points'] < amount:
        return False, "Insufficient points"
    
    if amount <= 0:
        return False, "Invalid amount"
    
    # Execute transfer
    user_referrals[from_user_id]['points'] -= amount
    user_referrals[to_user_id]['points'] += amount
    
    # Log transaction
    transfer_record = {
        'id': str(uuid.uuid4())[:8],
        'from_user': from_user_id,
        'to_user': to_user_id,
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    point_transfers.append(transfer_record)
    
    logger.info(f"Transferred {amount} points from {from_user_id} to {to_user_id}")
    return True, "Transfer successful"

# Helper functions
def is_admin(user_id):
    return user_id in ADMIN_IDS

def create_inline_keyboard(buttons):
    return InlineKeyboardMarkup(buttons)

def get_user_last_booking(user_id):
    """Get user's last booking"""
    user_bookings = [b for b in bookings if b['student_id'] == user_id]
    if user_bookings:
        return max(user_bookings, key=lambda x: x.get('timestamp', ''))
    return None

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Handle referral code from start command
    referred_by = None
    if context.args:
        referral_code = context.args[0]
        referred_by = get_user_by_referral_code(referral_code)
        if referred_by and referred_by != user.id:
            logger.info(f"User {user.id} referred by {referred_by} with code {referral_code}")

    # Store user information
    user_states[user.id] = {
        'username': user.username or "No username set",
        'full_name': user.full_name or "Unknown User",
        'chat_id': chat_id
    }
    
    # Initialize referral data for new users
    initialize_user_referral(user.id, referred_by)

    welcome_message = f"""💋 Welcome to SOLCAM! 💋

Hello {user.first_name}! 👋

I'm your personal beautiful girls booking assistant. Here's what I can help you with:

🩷 For Girls:
• Browse amazing beautiful cam girls
• View detailed profiles
• Book sessions
• Secure Bitcoin payments
• Earn points through referrals

Ready to start BOOM BOOM 💦? Choose an option below!

💬 Need Support? Contact us: {ADMIN_USERNAME}"""

    keyboard = [
        [InlineKeyboardButton("💋 Browse Models", callback_data='check_teachers')],
        [InlineKeyboardButton("👤 My Profile", callback_data='user_profile')],
        [InlineKeyboardButton("🎁 Referral System", callback_data='referral_menu')],
        [InlineKeyboardButton("❓ Help", callback_data='help_menu')],
        [InlineKeyboardButton("🌐 Social Media", callback_data='social_media')]
    ]

    # Add admin panel button only for admins
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data='admin')])

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, welcome_message, reply_markup=reply_markup)

# User profile system
async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    # Get user referral data
    referral_data = user_referrals.get(user_id, {})
    
    # Get last booking
    last_booking = get_user_last_booking(user_id)
    
    # Build profile message
    profile_message = f"""👤 YOUR PROFILE 👤
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆔 User ID: {user_id}
👤 Name: {user.full_name or 'Not set'}
🏷️ Username: @{user.username or 'Not set'}

💰 POINTS & REFERRALS:
🎯 Current Points: {referral_data.get('points', 0)}
📊 Total Earned: {referral_data.get('total_earned', 0)}
👥 Referrals Made: {len(referral_data.get('referrals', []))}
🔗 Your Referral Code: {referral_data.get('referral_code', 'N/A')}

📋 LAST ORDER:"""

    if last_booking:
        status_emoji = {
            'confirmed': '✅',
            'pending': '⏳',
            'rejected': '❌'
        }.get(last_booking.get('status', 'pending'), '⏳')
        
        profile_message += f"""
👩 Girl: {last_booking.get('teacher_name', 'N/A')}
📅 Date: {last_booking.get('date', 'N/A')}
⏰ Time: {last_booking.get('time', 'N/A')}
{status_emoji} Status: {last_booking.get('status', 'pending').title()}
💸 Amount: ${last_booking.get('price', 'N/A')}"""
    else:
        profile_message += "\nNo orders yet"

    profile_message += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("🎁 Referral Menu", callback_data='referral_menu')],
        [InlineKeyboardButton("💸 Transfer Points", callback_data='transfer_points')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, profile_message, reply_markup=reply_markup)

# Referral system menu
async def show_referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    referral_data = user_referrals.get(user_id, {})
    referral_code = referral_data.get('referral_code', 'N/A')
    
    referral_message = f"""🎁 REFERRAL SYSTEM 🎁
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💎 Earn SolCam Points by referring friends!

🔗 Your Referral Code: `{referral_code}`
👥 Total Referrals: {len(referral_data.get('referrals', []))}
💰 Points Balance: {referral_data.get('points', 0)}
🎯 Total Earned: {referral_data.get('total_earned', 0)}

📝 HOW IT WORKS:
1️⃣ Share your referral link with friends
2️⃣ They join using your link
3️⃣ You earn 1 point per referral
4️⃣ Use points to book models!

🔗 Your Referral Link:
`https://t.me/{context.bot.username}?start={referral_code}`

💡 Share this link to start earning points!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = [
        [InlineKeyboardButton("📋 Copy Referral Link", callback_data=f'copy_referral_{referral_code}')],
        [InlineKeyboardButton("💸 Transfer Points", callback_data='transfer_points')],
        [InlineKeyboardButton("📊 Referral Stats", callback_data='referral_stats')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, referral_message, reply_markup=reply_markup)

# Help menu
async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    help_message = """❓ HELP CENTER ❓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to SolCam Help Center! 
Choose what you need help with:

🔍 Browse our comprehensive guides and support options below."""

    keyboard = [
        [InlineKeyboardButton("📖 How to Use", callback_data='how_it_works')],
        [InlineKeyboardButton("💬 Contact Support", callback_data='contact_support')],
        [InlineKeyboardButton("👩‍💼 Become a Model", callback_data='become_model')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, help_message, reply_markup=reply_markup)

# Social media menu
async def show_social_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    social_message = """🌐 FOLLOW US ON SOCIAL MEDIA 🌐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stay connected with SolCam community!

📱 Join our channels for updates, announcements, and exclusive content:

🚀 Get the latest news and updates
💬 Connect with other users
🎁 Exclusive promotions and offers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = [
        [InlineKeyboardButton("📱 Telegram Community", url=TELEGRAM_COMMUNITY)],
        [InlineKeyboardButton("🐦 Follow us on X", url=X_ACCOUNT)],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, social_message, reply_markup=reply_markup)

# Point transfer system
async def handle_point_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    current_points = user_referrals.get(user_id, {}).get('points', 0)
    
    transfer_message = f"""💸 TRANSFER POINTS 💸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Your Current Balance: {current_points} points

📝 To transfer points:
1️⃣ Click "Start Transfer" below
2️⃣ Send the recipient's User ID
3️⃣ Send the amount to transfer

⚠️ Note: Transfers are irreversible!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = [
        [InlineKeyboardButton("🚀 Start Transfer", callback_data='start_transfer')],
        [InlineKeyboardButton("📊 Transfer History", callback_data='transfer_history')],
        [InlineKeyboardButton("🔙 Back", callback_data='user_profile')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, transfer_message, reply_markup=reply_markup)

# Admin panel
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    total_users = len(user_referrals)
    total_points = sum(data['points'] for data in user_referrals.values())
    total_referrals = sum(len(data['referrals']) for data in user_referrals.values())

    admin_message = f"""🔧 ADMIN CONTROL PANEL 🔧
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 Welcome, Admin {user.first_name}!

📊 System Status:
• Models: {len(teachers)}
• Bookings: {len(bookings)}
• Pending Payments: {len(pending_payments)}
• Total Users: {total_users}
• Total Points: {total_points}
• Total Referrals: {total_referrals}
• Active Admins: {len(ADMIN_IDS)}

Choose an admin action below:"""

    keyboard = [
        [InlineKeyboardButton("💋 Manage Models", callback_data='manage_teachers')],
        [InlineKeyboardButton("💰 Set Point Prices", callback_data='manage_point_prices')],
        [InlineKeyboardButton("📋 View Bookings", callback_data='view_bookings')],
        [InlineKeyboardButton("💸 Pending Payments", callback_data='view_payments')],
        [InlineKeyboardButton("📊 User Statistics", callback_data='user_stats')],
        [InlineKeyboardButton("➕ Add New Model", callback_data='add_teacher')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, admin_message, reply_markup=reply_markup)

# Show available teachers
async def show_available_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if not teachers:
        await context.bot.send_message(chat_id, '❌ No models available at the moment.')
        return

    # Header message
    header_message = """🔥 OUR AMAZING GIRLS 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose your perfect beautiful girls from our curated selection and have fun with your lady 💦 🥵!"""

    await context.bot.send_message(chat_id, header_message)

    # Send each teacher as individual card
    for teacher in teachers:
        if teacher['available']:
            point_price = teacher_point_prices.get(teacher['id'], 'Not set')
            
            teacher_card = f"""👙 Name: {teacher['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

😘 Age: {teacher['age']} years

😈 Interested: {', '.join(teacher['subjects'])}

💸 Rate: ${teacher['price']}/hour
🎯 Points: {point_price} points/hour

⭐ Rating: {teacher.get('rating', 'N/A')}/5.0

👙 Why Choose {teacher['name'].split()[0]}:
"{teacher.get('why_choose', 'Professional model.')}"

💡 Experience: {teacher.get('experience', 'Experienced educator')}

✅ Status: Available Now

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

            keyboard = [
                [InlineKeyboardButton("🍑 View Full Profile", callback_data=f"profile_teacher_{teacher['id']}")],
                [InlineKeyboardButton("💃 Book Me😘", callback_data=f"book_teacher_{teacher['id']}")]
            ]
            reply_markup = create_inline_keyboard(keyboard)

            try:
                if teacher.get('photo'):
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=teacher['photo'],
                        caption=teacher_card,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=teacher_card,
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Error sending model card for {teacher['name']}: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=teacher_card,
                    reply_markup=reply_markup
                )

# Show detailed teacher profile
async def show_teacher_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    chat_id = update.effective_chat.id

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)

    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    point_price = teacher_point_prices.get(teacher_id, 'Not set')

    profile_text = f"""🌟 {teacher['name']} - Full Profile 🌟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💃 PERSONAL INFO:
🎂 Age: {teacher['age']} years
🔥 Specializes in: {', '.join(teacher['subjects'])}
⭐ Rating: {teacher.get('rating', 'N/A')}/5.0

😈 Interested:
{teacher.get('education', 'Not specified')}

💄 EXPERIENCE:
{teacher.get('experience', 'Not specified')}

📝 ABOUT {teacher['name'].split()[0]}:
{teacher.get('bio', 'Professional with this field.')}

🎯 WHY CHOOSE {teacher['name'].split()[0]}:
{teacher.get('why_choose', 'loyalty and trust also beauty.')}

💸 PRICING:
USD Rate: ${teacher['price']}/hour
Points Rate: {point_price} points/hour
⭐ Status: {'✅ Available Now' if teacher['available'] else '❌ Currently Unavailable'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💋 Want her? Tap below to book your private moment!"""

    keyboard = [
        [InlineKeyboardButton("💋 Book Me Now 💋", callback_data=f"book_teacher_{teacher['id']}")],
        [InlineKeyboardButton("← Back to All Models", callback_data='check_teachers')]
    ]
    reply_markup = create_inline_keyboard(keyboard)

    try:
        if teacher.get('photo'):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=teacher['photo'],
                caption=profile_text,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=profile_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error sending teacher profile for {teacher['name']}: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=profile_text,
            reply_markup=reply_markup
        )

# Handle teacher booking (modified to include points option)
async def handle_book_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Get user info
    user_info = user_states.get(user_id, {})
    student_username = user_info.get('username', 'No username set')
    student_full_name = user_info.get('full_name', 'Unknown User')

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)

    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    if not teacher['available']:
        await context.bot.send_message(chat_id, '❌ This Model is currently unavailable.')
        return

    # Show payment options
    user_points = user_referrals.get(user_id, {}).get('points', 0)
    point_price = teacher_point_prices.get(teacher_id, None)
    
    booking_message = f"""💋 BOOKING: {teacher['name']} 💋
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose your payment method:

💸 USD Payment: ${teacher['price']}/hour
🎯 Points Payment: {point_price if point_price else 'Not available'} points/hour

💰 Your Points Balance: {user_points}

Select payment method below:"""

    keyboard = [
        [InlineKeyboardButton("💸 Pay with USD", callback_data=f"book_usd_{teacher_id}")],
    ]
    
    # Only show points option if admin has set point price and user has enough points
    if point_price and user_points >= point_price:
        keyboard.append([InlineKeyboardButton("🎯 Pay with Points", callback_data=f"book_points_{teacher_id}")])
    elif point_price:
        keyboard.append([InlineKeyboardButton(f"🚫 Insufficient Points ({user_points}/{point_price})", callback_data="insufficient_points")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"profile_teacher_{teacher_id}")])
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, booking_message, reply_markup=reply_markup)

# Handle USD booking (existing functionality)
async def handle_usd_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Get user info
    user_info = user_states.get(user_id, {})
    student_username = user_info.get('username', 'No username set')
    student_full_name = user_info.get('full_name', 'Unknown User')

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)

    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    # Create booking
    booking_id = str(uuid.uuid4())[:8]
    booking = {
        'id': booking_id,
        'student_id': user_id,
        'student_username': student_username,
        'student_name': student_full_name,
        'teacher_id': teacher_id,
        'teacher_name': teacher['name'],
        'price': teacher['price'],
        'payment_method': 'USD',
        'status': 'pending_payment',
        'timestamp': datetime.now().isoformat(),
        'date': '',
        'time': '',
        'duration': '1 hour'
    }

    bookings.append(booking)
    logger.info(f"Booking created: {booking_id} for user {user_id}")

    booking_message = f"""✅ BOOKING CREATED! ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Booking Details:
🆔 Booking ID: {booking_id}
👩 Model: {teacher['name']}
💰 Amount: ${teacher['price']}
💳 Payment: USD (Bitcoin)

⏳ Status: Pending Payment

📝 Next Steps:
1️⃣ Complete Bitcoin payment
2️⃣ Upload payment proof
3️⃣ Wait for confirmation
4️⃣ Receive booking details

💎 Bitcoin Wallet Address:
`{BTC_WALLET}`

⚠️ Important: Send exactly ${teacher['price']} worth of Bitcoin to complete your booking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = [
        [InlineKeyboardButton("📤 Upload Payment Proof", callback_data=f"upload_payment_{booking_id}")],
        [InlineKeyboardButton("❌ Cancel Booking", callback_data=f"cancel_booking_{booking_id}")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, booking_message, reply_markup=reply_markup)

# Handle points booking (new functionality)
async def handle_points_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Get user info
    user_info = user_states.get(user_id, {})
    student_username = user_info.get('username', 'No username set')
    student_full_name = user_info.get('full_name', 'Unknown User')

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    point_price = teacher_point_prices.get(teacher_id)
    user_points = user_referrals.get(user_id, {}).get('points', 0)

    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    if not point_price:
        await context.bot.send_message(chat_id, '❌ Points payment not available for this model.')
        return

    if user_points < point_price:
        await context.bot.send_message(chat_id, f'❌ Insufficient points. You need {point_price} points but have {user_points}.')
        return

    # Deduct points
    user_referrals[user_id]['points'] -= point_price

    # Create booking
    booking_id = str(uuid.uuid4())[:8]
    booking = {
        'id': booking_id,
        'student_id': user_id,
        'student_username': student_username,
        'student_name': student_full_name,
        'teacher_id': teacher_id,
        'teacher_name': teacher['name'],
        'price': point_price,
        'payment_method': 'Points',
        'status': 'confirmed',
        'timestamp': datetime.now().isoformat(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
        'duration': '1 hour'
    }

    bookings.append(booking)
    logger.info(f"Points booking created: {booking_id} for user {user_id}")

    booking_message = f"""✅ BOOKING CONFIRMED! ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Booking Details:
🆔 Booking ID: {booking_id}
👩 Model: {teacher['name']}
💰 Amount: {point_price} points
💳 Payment: Points (Auto-confirmed)

✅ Status: Confirmed

🎉 Congratulations! Your booking has been automatically confirmed.

📱 Contact Information:
Model will contact you shortly via Telegram.

💰 Remaining Points: {user_referrals[user_id]['points']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    keyboard = [
        [InlineKeyboardButton("👤 My Profile", callback_data='user_profile')],
        [InlineKeyboardButton("💋 Browse More Models", callback_data='check_teachers')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, booking_message, reply_markup=reply_markup)

    # Notify admins
    admin_notification = f"""🔔 NEW POINTS BOOKING 🔔

📋 Booking ID: {booking_id}
👤 Student: {student_full_name} (@{student_username})
👩 Model: {teacher['name']}
💰 Amount: {point_price} points
✅ Status: Auto-confirmed

Action: Please arrange model contact."""

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_notification)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# Additional helper functions for new features

async def handle_referral_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    referral_data = user_referrals.get(user_id, {})
    referrals_list = referral_data.get('referrals', [])
    
    stats_message = f"""📊 REFERRAL STATISTICS 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 Total Referrals: {len(referrals_list)}
💰 Points Earned: {referral_data.get('total_earned', 0)}
🎯 Current Balance: {referral_data.get('points', 0)}

📈 Recent Referrals:"""

    if referrals_list:
        recent_referrals = referrals_list[-5:]  # Show last 5
        for ref_id in recent_referrals:
            ref_user = user_states.get(ref_id, {})
            stats_message += f"\n• {ref_user.get('full_name', 'Unknown')} (ID: {ref_id})"
    else:
        stats_message += "\nNo referrals yet"

    stats_message += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Referrals", callback_data='referral_menu')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, stats_message, reply_markup=reply_markup)

async def handle_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    how_it_works_message = """📖 HOW TO USE SOLCAM 📖
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to SolCam! Here's how to get started:

🔥 BOOKING MODELS:
1️⃣ Browse available models
2️⃣ View detailed profiles
3️⃣ Choose payment method (USD/Points)
4️⃣ Complete booking
5️⃣ Enjoy your session!

🎁 EARNING POINTS:
1️⃣ Share your referral link
2️⃣ Friends join using your link
3️⃣ Earn 1 point per referral
4️⃣ Use points to book models

💸 PAYMENT METHODS:
• Bitcoin (USD payments)
• Points (earned through referrals)

🔒 SECURITY:
• All payments secured
• Privacy protected
• 24/7 support available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Need more help? Contact support!"""

    keyboard = [
        [InlineKeyboardButton("💬 Contact Support", callback_data='contact_support')],
        [InlineKeyboardButton("🔙 Back to Help", callback_data='help_menu')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, how_it_works_message, reply_markup=reply_markup)

async def handle_contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    support_message = f"""💬 CONTACT SUPPORT 💬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need help? Our support team is here for you!

📞 Support Options:
• Direct Message: {ADMIN_USERNAME}
• Telegram Community: @SolCamSupport
• Response Time: 24/7

🔍 Common Issues:
• Payment problems
• Booking questions
• Account issues
• Technical support

💡 Tips:
• Include your User ID in messages
• Describe your issue clearly
• Attach screenshots if needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We're here to help! 🤝"""

    keyboard = [
        [InlineKeyboardButton("💬 Message Support", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back to Help", callback_data='help_menu')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, support_message, reply_markup=reply_markup)

async def handle_become_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    become_model_message = f"""👩‍💼 BECOME A MODEL 👩‍💼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Interested in joining our model team?

💎 BENEFITS:
• Flexible working hours
• High earning potential
• Safe and secure platform
• Professional support

📋 REQUIREMENTS:
• 18+ years old
• Reliable internet connection
• Professional attitude
• Good communication skills

📝 APPLICATION PROCESS:
1️⃣ Contact our team
2️⃣ Complete application
3️⃣ Profile verification
4️⃣ Platform training
5️⃣ Start earning!

💰 EARNINGS:
• Competitive rates
• Weekly payments
• Performance bonuses
• Referral rewards

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ready to start your journey? 🚀"""

    keyboard = [
        [InlineKeyboardButton("📝 Apply Now", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("💬 Ask Questions", callback_data='contact_support')],
        [InlineKeyboardButton("🔙 Back to Help", callback_data='help_menu')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, support_message, reply_markup=reply_markup)

# Admin functions for point management
async def manage_point_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    prices_message = """💰 POINT PRICES MANAGEMENT 💰
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current point prices for models:

"""

    for teacher in teachers:
        point_price = teacher_point_prices.get(teacher['id'], 'Not set')
        prices_message += f"👩 {teacher['name']}: {point_price} points/hour\n"

    prices_message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nSelect a model to set point price:"

    keyboard = []
    for teacher in teachers:
        keyboard.append([InlineKeyboardButton(f"💎 {teacher['name']}", callback_data=f"set_points_{teacher['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')])
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, prices_message, reply_markup=reply_markup)

async def show_user_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    total_users = len(user_referrals)
    total_points = sum(data['points'] for data in user_referrals.values())
    total_referrals = sum(len(data['referrals']) for data in user_referrals.values())
    
    # Top referrers
    top_referrers = sorted(user_referrals.items(), key=lambda x: len(x[1]['referrals']), reverse=True)[:5]
    
    stats_message = f"""📊 USER STATISTICS 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 OVERVIEW:
• Total Users: {total_users}
• Total Points: {total_points}
• Total Referrals: {total_referrals}
• Point Transfers: {len(point_transfers)}

🏆 TOP REFERRERS:"""

    for i, (user_id, data) in enumerate(top_referrers, 1):
        user_info = user_states.get(user_id, {})
        user_name = user_info.get('full_name', 'Unknown')
        referral_count = len(data['referrals'])
        stats_message += f"\n{i}. {user_name} - {referral_count} referrals"

    stats_message += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
    ]
    
    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, stats_message, reply_markup=reply_markup)

# Message handlers for point transfer and admin operations
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    text = update.message.text
    chat_id = update.effective_chat.id

    # Handle point transfer states and teacher management
    if user_id in teacher_edit_states:
        state = teacher_edit_states[user_id]
        
        if state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_TRANSFER_USER']:
            try:
                target_user_id = int(text.strip())
                if target_user_id not in user_referrals:
                    await context.bot.send_message(chat_id, '❌ User not found. Please enter a valid User ID.')
                    return
                
                teacher_edit_states[user_id]['target_user'] = target_user_id
                teacher_edit_states[user_id]['state'] = TEACHER_EDIT_STATES['WAITING_FOR_TRANSFER_AMOUNT']
                
                target_user_info = user_states.get(target_user_id, {})
                target_name = target_user_info.get('full_name', 'Unknown User')
                
                await context.bot.send_message(
                    chat_id, 
                    f"✅ Target user found: {target_name} (ID: {target_user_id})\n\n💰 Your current balance: {user_referrals[user_id]['points']} points\n\nNow send the amount to transfer:"
                )
                
            except ValueError:
                await context.bot.send_message(chat_id, '❌ Please enter a valid numeric User ID.')
                
        elif state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_TRANSFER_AMOUNT']:
            try:
                amount = int(text.strip())
                target_user_id = state['target_user']
                
                success, message = transfer_points(user_id, target_user_id, amount)
                
                if success:
                    target_user_info = user_states.get(target_user_id, {})
                    target_name = target_user_info.get('full_name', 'Unknown User')
                    
                    await context.bot.send_message(
                        chat_id, 
                        f"✅ Transfer successful!\n\n💸 Transferred: {amount} points\n👤 To: {target_name}\n💰 Your new balance: {user_referrals[user_id]['points']} points"
                    )
                    
                    # Notify recipient
                    try:
                        sender_info = user_states.get(user_id, {})
                        sender_name = sender_info.get('full_name', 'Unknown User')
                        recipient_chat_id = user_states.get(target_user_id, {}).get('chat_id')
                        
                        if recipient_chat_id:
                            await context.bot.send_message(
                                recipient_chat_id,
                                f"🎁 You received {amount} points from {sender_name}!\n\n💰 Your new balance: {user_referrals[target_user_id]['points']} points"
                            )
                    except Exception as e:
                        logger.error(f"Failed to notify recipient: {e}")
                        
                else:
                    await context.bot.send_message(chat_id, f"❌ Transfer failed: {message}")
                    
                del teacher_edit_states[user_id]
                
            except ValueError:
                await context.bot.send_message(chat_id, '❌ Please enter a valid numeric amount.')
                
        elif state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_POINT_PRICE']:
            try:
                price = int(text.strip())
                teacher_id = state['teacher_id']
                
                teacher_point_prices[teacher_id] = price
                teacher = next((t for t in teachers if t['id'] == teacher_id), None)
                
                await context.bot.send_message(
                    chat_id,
                    f"✅ Point price set successfully!\n\n👩 Model: {teacher['name']}\n💎 Price: {price} points/hour"
                )
                
                del teacher_edit_states[user_id]
                
            except ValueError:
                await context.bot.send_message(chat_id, '❌ Please enter a valid numeric price.')
                
        elif state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_VALUE']:
            field = state['field']
            teacher_id = state['teacher_id']
            
            teacher = next((t for t in teachers if t['id'] == teacher_id), None)
            if not teacher:
                await context.bot.send_message(chat_id, '❌ Model not found.')
                del teacher_edit_states[user_id]
                return
            
            # Process the new value based on field type
            try:
                if field == 'age':
                    value = int(text.strip())
                elif field == 'price':
                    value = float(text.strip())
                elif field == 'rating':
                    value = float(text.strip())
                    if value < 0 or value > 5:
                        await context.bot.send_message(chat_id, '❌ Rating must be between 0 and 5.')
                        return
                elif field == 'subjects':
                    value = [s.strip() for s in text.split(',')]
                else:
                    value = text.strip()
                
                # Update the teacher
                teacher[field] = value
                
                await context.bot.send_message(
                    chat_id,
                    f"✅ Updated {field} for {teacher['name']} successfully!\n\n📝 New value: {value}"
                )
                
                del teacher_edit_states[user_id]
                
            except ValueError:
                await context.bot.send_message(chat_id, '❌ Please enter a valid value for this field.')
                
        elif state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_NEW_TEACHER']:
            # Handle adding new teacher step by step
            await handle_add_teacher_step(update, context, text)

# Admin management functions
async def manage_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    if not teachers:
        await context.bot.send_message(chat_id, '❌ No model available.')
        return

    management_message = """💃 MODEL MANAGEMENT 💃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select a teacher to edit their profile:"""

    keyboard = []
    for teacher in teachers:
        keyboard.append([InlineKeyboardButton(f"✏️ Edit {teacher['name']}", callback_data=f"edit_teacher_{teacher['id']}")])

    keyboard.append([InlineKeyboardButton("❌ Remove Model", callback_data='remove_teacher_menu')])
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')])

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, management_message, reply_markup=reply_markup)

async def show_bookings_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    if not bookings:
        await context.bot.send_message(chat_id, '❌ No bookings yet.')
        return

    bookings_list = '📊 BOOKINGS MANAGEMENT 📊\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'

    for i, booking in enumerate(bookings, 1):
        username_display = f"@{booking.get('student_username', 'No username')}" if booking.get('student_username') != "No username set" else "❌ No username"

        bookings_list += f"""📋 Booking #{i}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 STUDENT INFO:
📝 Name: {booking.get('student_name', 'Unknown')}
🏷️ Username: {username_display}
🆔 User ID: {booking['student_id']}

💃 MODEL: {booking['teacher_name']}
💰 PRICE: ${booking['price']}
📅 DATE: {booking['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
🔄 STATUS: {booking['status']}

🆔 Booking ID: {booking['id']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    await context.bot.send_message(chat_id, bookings_list)

async def show_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    if not pending_payments:
        await context.bot.send_message(chat_id, '✅ No pending payments.')
        return

    payments_list = '💰 PENDING PAYMENTS 💰\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'

    for booking_id, booking in pending_payments.items():
        username_display = f"@{booking.get('student_username', 'No username')}" if booking.get('student_username') != "No username set" else "❌ No username"

        payments_list += f"""💳 Payment #{booking_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 USER: {booking.get('student_name', 'Unknown')}
🏷️ USERNAME: {username_display}
💃 MODEL: {booking['teacher_name']}
💰 AMOUNT: ${booking['price']}
📅 DATE: {booking['created_at'].strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    keyboard = []
    for booking_id in pending_payments.keys():
        keyboard.append([
            InlineKeyboardButton(f"✅ Confirm {booking_id}", callback_data=f"confirm_payment_{booking_id}"),
            InlineKeyboardButton(f"❌ Reject {booking_id}", callback_data=f"reject_payment_{booking_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')])
    reply_markup = create_inline_keyboard(keyboard)

    await context.bot.send_message(chat_id, payments_list, reply_markup=reply_markup)

async def add_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    # Set user state for adding teacher
    teacher_edit_states[user.id] = {
        'state': TEACHER_EDIT_STATES['WAITING_FOR_NEW_TEACHER'],
        'step': 'name',
        'teacher_data': {}
    }

    add_message = """➕ ADD NEW MODEL ➕
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Let's add a new model to the system!

📝 Step 1: model Name
Please enter the model's full name:"""

    await context.bot.send_message(chat_id, add_message)

async def edit_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await context.bot.send_message(chat_id, '❌ model not found.')
        return

    edit_message = f"""✏️ EDIT MODEL PROFILE ✏️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👨‍🏫 Current Profile: {teacher['name']}

Select field to edit:"""

    keyboard = [
        [InlineKeyboardButton("🩷 Name", callback_data=f"edit_field_name_{teacher_id}")],
        [InlineKeyboardButton("😘 Age", callback_data=f"edit_field_age_{teacher_id}")],
        [InlineKeyboardButton("💰 Price", callback_data=f"edit_field_price_{teacher_id}")],
        [InlineKeyboardButton("🥵 Interasted", callback_data=f"edit_field_subjects_{teacher_id}")],
        [InlineKeyboardButton("🎯 Why Choose", callback_data=f"edit_field_why_choose_{teacher_id}")],
        [InlineKeyboardButton("📖 Bio", callback_data=f"edit_field_bio_{teacher_id}")],
        [InlineKeyboardButton("🎓 Education", callback_data=f"edit_field_education_{teacher_id}")],
        [InlineKeyboardButton("😈 Experience", callback_data=f"edit_field_experience_{teacher_id}")],
        [InlineKeyboardButton("⭐ Rating", callback_data=f"edit_field_rating_{teacher_id}")],
        [InlineKeyboardButton("📸 Photo URL", callback_data=f"edit_field_photo_{teacher_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data='manage_teachers')]
    ]

    reply_markup = create_inline_keyboard(keyboard)
    await context.bot.send_message(chat_id, edit_message, reply_markup=reply_markup)

async def remove_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    # Remove teacher from list
    teachers.remove(teacher)
    
    # Remove teacher from point prices if exists
    if teacher_id in teacher_point_prices:
        del teacher_point_prices[teacher_id]

    await context.bot.send_message(
        chat_id, 
        f"✅ Model {teacher['name']} has been removed successfully!"
    )

async def handle_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: str) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    if booking_id not in pending_payments:
        await context.bot.send_message(chat_id, '❌ Payment not found.')
        return

    booking = pending_payments[booking_id]
    
    # Update booking status
    for b in bookings:
        if b['id'] == booking_id:
            b['status'] = 'confirmed'
            break
    
    # Remove from pending payments
    del pending_payments[booking_id]
    
    # Notify customer
    try:
        await context.bot.send_message(
            booking['student_id'],
            f"✅ Payment confirmed!\n\n💋 Your booking with {booking['teacher_name']} is now active!\n\n🎯 Next Steps:\n• Your model will contact you within 5 minutes\n• Have fun! 💦\n\n📞 Support: {ADMIN_USERNAME}"
        )
    except:
        pass  # User might have blocked bot
    
    await context.bot.send_message(
        chat_id, 
        f"✅ Payment confirmed for booking {booking_id}!"
    )

async def handle_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: str) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    if booking_id not in pending_payments:
        await context.bot.send_message(chat_id, '❌ Payment not found.')
        return

    booking = pending_payments[booking_id]
    
    # Update booking status
    for b in bookings:
        if b['id'] == booking_id:
            b['status'] = 'rejected'
            break
    
    # Remove from pending payments
    del pending_payments[booking_id]
    
    # Notify customer
    try:
        await context.bot.send_message(
            booking['student_id'],
            f"❌ Payment rejected!\n\n💳 Your payment for booking {booking_id} was not verified.\n\n🔄 Please:\n• Double-check the payment amount\n• Ensure payment was sent to correct wallet\n• Try again or contact support\n\n📞 Support: {ADMIN_USERNAME}"
        )
    except:
        pass  # User might have blocked bot
    
    await context.bot.send_message(
        chat_id, 
        f"❌ Payment rejected for booking {booking_id}!"
    )

async def handle_upload_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: str) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Check if booking exists
    booking = next((b for b in bookings if b['id'] == booking_id), None)
    if not booking:
        await context.bot.send_message(chat_id, '❌ Booking not found.')
        return

    # Check if user is the owner of this booking
    if booking['student_id'] != user_id:
        await context.bot.send_message(chat_id, '❌ You can only upload payment proof for your own bookings.')
        return

    # Set user state to expect payment proof photo
    user_states[user_id] = user_states.get(user_id, {})
    user_states[user_id]['waiting_for_payment_proof'] = booking_id

    await context.bot.send_message(
        chat_id,
        f"📤 UPLOAD PAYMENT PROOF\n\n"
        f"🆔 Booking ID: {booking_id}\n"
        f"💰 Amount: ${booking['price']}\n"
        f"📝 Please send a screenshot of your Bitcoin payment transaction.\n\n"
        f"📸 Send the image now:"
    )

async def handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, teacher_id: int) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if not is_admin(user.id):
        await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
        return

    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await context.bot.send_message(chat_id, '❌ Model not found.')
        return

    # Set user state for editing
    teacher_edit_states[user.id] = {
        'state': TEACHER_EDIT_STATES['WAITING_FOR_VALUE'],
        'field': field,
        'teacher_id': teacher_id
    }

    field_names = {
        'name': 'Name',
        'age': 'Age',
        'price': 'Price (USD)',
        'subjects': 'Interests',
        'why_choose': 'Why Choose',
        'bio': 'Bio',
        'education': 'Education',
        'experience': 'Experience',
        'rating': 'Rating (0-5)',
        'photo': 'Photo URL'
    }

    current_value = teacher.get(field, 'Not set')
    if field == 'subjects' and isinstance(current_value, list):
        current_value = ', '.join(current_value)

    await context.bot.send_message(
        chat_id,
        f"✏️ Edit {field_names.get(field, field.title())}\n\n📝 Current value: {current_value}\n\n💬 Send new value:"
    )

async def handle_add_teacher_step(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    
    if user_id not in teacher_edit_states:
        return
    
    state = teacher_edit_states[user_id]
    step = state['step']
    teacher_data = state['teacher_data']
    
    if step == 'name':
        teacher_data['name'] = text.strip()
        state['step'] = 'age'
        await context.bot.send_message(chat_id, f"✅ Name set: {text.strip()}\n\n📝 Step 2: Age\nPlease enter the model's age:")
    
    elif step == 'age':
        try:
            teacher_data['age'] = int(text.strip())
            state['step'] = 'price'
            await context.bot.send_message(chat_id, f"✅ Age set: {text.strip()}\n\n📝 Step 3: Price\nPlease enter the hourly rate (USD):")
        except ValueError:
            await context.bot.send_message(chat_id, "❌ Please enter a valid age number.")
    
    elif step == 'price':
        try:
            teacher_data['price'] = float(text.strip())
            state['step'] = 'subjects'
            await context.bot.send_message(chat_id, f"✅ Price set: ${text.strip()}\n\n📝 Step 4: Interests\nPlease enter interests (comma-separated):")
        except ValueError:
            await context.bot.send_message(chat_id, "❌ Please enter a valid price number.")
    
    elif step == 'subjects':
        teacher_data['subjects'] = [s.strip() for s in text.split(',')]
        state['step'] = 'bio'
        await context.bot.send_message(chat_id, f"✅ Interests set: {text.strip()}\n\n📝 Step 5: Bio\nPlease enter a short bio:")
    
    elif step == 'bio':
        teacher_data['bio'] = text.strip()
        state['step'] = 'photo'
        await context.bot.send_message(chat_id, f"✅ Bio set!\n\n📝 Step 6: Photo\nPlease send a photo URL (starting with http/https) or upload a photo directly:")
    
    elif step == 'photo':
        # Handle photo URL as text input
        if text.strip().startswith('http'):
            teacher_data['photo'] = text.strip()
            
            # Generate new ID
            new_id = max([t['id'] for t in teachers], default=0) + 1
            
            # Create new teacher
            new_teacher = {
                'id': new_id,
                'name': teacher_data['name'],
                'age': teacher_data['age'],
                'price': teacher_data['price'],
                'subjects': teacher_data['subjects'],
                'bio': teacher_data['bio'],
                'photo': teacher_data['photo'],
                'available': True,
                'rating': 5.0,
                'education': 'Not specified',
                'experience': 'Professional model',
                'why_choose': 'Professional and reliable service'
            }
            
            teachers.append(new_teacher)
            
            await context.bot.send_message(
                chat_id,
                f"✅ NEW MODEL ADDED SUCCESSFULLY! ✅\n\n💃 Name: {new_teacher['name']}\n😘 Age: {new_teacher['age']}\n💰 Price: ${new_teacher['price']}\n🥵 Interests: {', '.join(new_teacher['subjects'])}\n\n🎉 Model is now available for booking!"
            )
            
            del teacher_edit_states[user_id]
        else:
            await context.bot.send_message(chat_id, "📸 Please send a valid photo URL or upload a photo directly.")

# Photo handler for payment proofs and teacher photos
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    
    # Check if user is in teacher editing state and waiting for photo
    if user_id in teacher_edit_states:
        state = teacher_edit_states[user_id]
        
        if state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_VALUE'] and state.get('field') == 'photo':
            # Get the photo file
            photo = update.message.photo[-1]  # Get the highest resolution photo
            file = await context.bot.get_file(photo.file_id)
            
            # For now, we'll use the file_id as the photo URL
            # In production, you'd upload this to a cloud storage service
            photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            
            teacher_id = state['teacher_id']
            teacher = next((t for t in teachers if t['id'] == teacher_id), None)
            
            if teacher:
                teacher['photo'] = photo_url
                await context.bot.send_message(
                    chat_id,
                    f"✅ Photo updated for {teacher['name']} successfully!"
                )
                del teacher_edit_states[user_id]
            else:
                await context.bot.send_message(chat_id, '❌ Model not found.')
                del teacher_edit_states[user_id]
        
        elif state['state'] == TEACHER_EDIT_STATES['WAITING_FOR_NEW_TEACHER'] and state.get('step') == 'photo':
            # Handle photo upload for new teacher
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            
            teacher_data = state['teacher_data']
            teacher_data['photo'] = photo_url
            
            # Generate new ID
            new_id = max([t['id'] for t in teachers], default=0) + 1
            
            # Create new teacher
            new_teacher = {
                'id': new_id,
                'name': teacher_data['name'],
                'age': teacher_data['age'],
                'price': teacher_data['price'],
                'subjects': teacher_data['subjects'],
                'bio': teacher_data['bio'],
                'photo': photo_url,
                'available': True,
                'rating': 5.0,
                'education': 'Not specified',
                'experience': 'Professional model',
                'why_choose': 'Professional and reliable service'
            }
            
            teachers.append(new_teacher)
            
            await context.bot.send_message(
                chat_id,
                f"✅ NEW MODEL ADDED SUCCESSFULLY! ✅\n\n💃 Name: {new_teacher['name']}\n😘 Age: {new_teacher['age']}\n💰 Price: ${new_teacher['price']}\n🥵 Interests: {', '.join(new_teacher['subjects'])}\n\n🎉 Model is now available for booking!"
            )
            
            del teacher_edit_states[user_id]
        
        else:
            await context.bot.send_message(chat_id, "📸 Photo received, but I'm not sure what to do with it. Please try again.")
    
    else:
        # Check if user is waiting to upload payment proof
        if user_id in user_states and 'waiting_for_payment_proof' in user_states[user_id]:
            booking_id = user_states[user_id]['waiting_for_payment_proof']
            
            # Get the photo file
            photo = update.message.photo[-1]  # Get the highest resolution photo
            file = await context.bot.get_file(photo.file_id)
            
            # Get booking details
            booking = next((b for b in bookings if b['id'] == booking_id), None)
            if not booking:
                await context.bot.send_message(chat_id, '❌ Booking not found.')
                del user_states[user_id]['waiting_for_payment_proof']
                return
            
            # Store payment proof in pending payments
            pending_payments[booking_id] = {
                'booking_id': booking_id,
                'student_id': user_id,
                'student_username': user.username or user.first_name,
                'teacher_name': booking['teacher_name'],
                'price': booking['price'],
                'photo_file_id': photo.file_id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Update booking status
            for b in bookings:
                if b['id'] == booking_id:
                    b['status'] = 'payment_submitted'
                    break
            
            # Clear the waiting state
            del user_states[user_id]['waiting_for_payment_proof']
            
            # Confirm to user
            await context.bot.send_message(
                chat_id,
                f"✅ Payment proof uploaded successfully!\n\n"
                f"🆔 Booking ID: {booking_id}\n"
                f"⏳ Your payment is now being reviewed by our admin team.\n"
                f"📧 You'll receive confirmation within 5-10 minutes.\n\n"
                f"📞 Support: {ADMIN_USERNAME}"
            )
            
            # Notify admin
            admin_message = f"💳 NEW PAYMENT PROOF RECEIVED\n\n"
            admin_message += f"🆔 Booking ID: {booking_id}\n"
            admin_message += f"👤 Student: @{user.username or user.first_name} (ID: {user_id})\n"
            admin_message += f"💃 Model: {booking['teacher_name']}\n"
            admin_message += f"💰 Amount: ${booking['price']}\n"
            admin_message += f"⏰ Submitted: {pending_payments[booking_id]['timestamp']}\n"
            
            keyboard = [
                [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_payment_{booking_id}")],
                [InlineKeyboardButton("❌ Reject Payment", callback_data=f"reject_payment_{booking_id}")]
            ]
            reply_markup = create_inline_keyboard(keyboard)
            
            # Send notification to all admins
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_photo(
                        admin_id,
                        photo=photo.file_id,
                        caption=admin_message,
                        reply_markup=reply_markup
                    )
                except:
                    pass  # Admin might have blocked bot
        
        else:
            # Handle generic payment proof photos
            await context.bot.send_message(
                chat_id,
                "📸 Payment proof received! Please forward this to the admin for verification.\n\n📞 Contact: @G_king123f"
            )

# Callback query handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Route to appropriate handlers
        if data == 'back_to_main':
            await start(update, context)
        elif data == 'check_teachers':
            await show_available_teachers(update, context)
        elif data == 'user_profile':
            await show_user_profile(update, context)
        elif data == 'referral_menu':
            await show_referral_menu(update, context)
        elif data == 'help_menu':
            await show_help_menu(update, context)
        elif data == 'social_media':
            await show_social_media(update, context)
        elif data == 'how_it_works':
            await handle_how_it_works(update, context)
        elif data == 'contact_support':
            await handle_contact_support(update, context)
        elif data == 'become_model':
            await handle_become_model(update, context)
        elif data == 'transfer_points':
            await handle_point_transfer(update, context)
        elif data == 'referral_stats':
            await handle_referral_stats(update, context)
        elif data == 'start_transfer':
            teacher_edit_states[user.id] = {
                'state': TEACHER_EDIT_STATES['WAITING_FOR_TRANSFER_USER']
            }
            await context.bot.send_message(
                chat_id,
                "💸 POINT TRANSFER\n\nPlease send the User ID of the person you want to transfer points to:"
            )
        elif data == 'admin':
            await admin(update, context)
        elif data == 'manage_point_prices':
            await manage_point_prices(update, context)
        elif data == 'user_stats':
            await show_user_statistics(update, context)
        elif data.startswith('profile_teacher_'):
            teacher_id = int(data.split('_')[2])
            await show_teacher_profile(update, context, teacher_id)
        elif data.startswith('book_teacher_'):
            teacher_id = int(data.split('_')[2])
            await handle_book_teacher(update, context, teacher_id)
        elif data.startswith('book_usd_'):
            teacher_id = int(data.split('_')[2])
            await handle_usd_booking(update, context, teacher_id)
        elif data.startswith('book_points_'):
            teacher_id = int(data.split('_')[2])
            await handle_points_booking(update, context, teacher_id)
        elif data.startswith('set_points_'):
            if is_admin(user.id):
                teacher_id = int(data.split('_')[2])
                teacher_edit_states[user.id] = {
                    'state': TEACHER_EDIT_STATES['WAITING_FOR_POINT_PRICE'],
                    'teacher_id': teacher_id
                }
                teacher = next((t for t in teachers if t['id'] == teacher_id), None)
                await context.bot.send_message(
                    chat_id,
                    f"💰 Setting point price for {teacher['name']}\n\nCurrent price: {teacher_point_prices.get(teacher_id, 'Not set')}\n\nSend new point price:"
                )
        elif data.startswith('copy_referral_'):
            referral_code = data.split('_')[2]
            bot_username = context.bot.username
            referral_link = f"https://t.me/{bot_username}?start={referral_code}"
            await context.bot.send_message(
                chat_id,
                f"📋 Your referral link has been copied!\n\n🔗 Link: `{referral_link}`\n\nShare this link with friends to earn points!"
            )
        elif data == 'insufficient_points':
            await context.bot.send_message(
                chat_id,
                "❌ You don't have enough points for this booking.\n\n💡 Earn more points by:\n• Referring friends\n• Receiving point transfers\n\n🎁 Share your referral link to start earning!"
            )
        
        # Admin panel handlers
        elif data == 'manage_teachers':
            await manage_teachers(update, context)
        elif data == 'view_bookings':
            await show_bookings_admin(update, context)
        elif data == 'view_payments':
            await show_pending_payments(update, context)
        elif data == 'add_teacher':
            await add_teacher(update, context)
        elif data.startswith('edit_teacher_'):
            teacher_id = int(data.split('_')[2])
            await edit_teacher(update, context, teacher_id)
        elif data.startswith('remove_teacher_'):
            teacher_id = int(data.split('_')[2])
            await remove_teacher(update, context, teacher_id)
        elif data.startswith('confirm_payment_'):
            booking_id = data.split('_')[2]
            await handle_confirm_payment(update, context, booking_id)
        elif data.startswith('reject_payment_'):
            booking_id = data.split('_')[2]
            await handle_reject_payment(update, context, booking_id)
        elif data.startswith('edit_field_'):
            parts = data.split('_')
            field = parts[2]
            teacher_id = int(parts[3])
            await handle_edit_field(update, context, field, teacher_id)
        elif data == 'remove_teacher_menu':
            if not is_admin(user.id):
                await context.bot.send_message(chat_id, '❌ Access denied. Admin only.')
            else:
                keyboard = [[InlineKeyboardButton(f"❌ Remove {teacher['name']}", callback_data=f"remove_teacher_{teacher['id']}")] for teacher in teachers]
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='manage_teachers')])
                reply_markup = create_inline_keyboard(keyboard)
                await context.bot.send_message(chat_id, '🗑️ Remove Teachers:', reply_markup=reply_markup)
        elif data.startswith('upload_payment_'):
            booking_id = data.split('_')[2]
            await handle_upload_payment_proof(update, context, booking_id)
        else:
            # Unknown callback data
            await context.bot.send_message(chat_id, "❌ Unknown action. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in callback query handler: {e}")
        await context.bot.send_message(chat_id, "❌ An error occurred. Please try again.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")

# Main function
def main() -> None:
    """Start the bot."""
    # Initialize data
    initialize_teachers()
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info("Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
