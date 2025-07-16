#!/usr/bin/env python3
"""
TELEGRAM BOT PAYMENT PROOF UPLOAD FIX
=====================================

This script contains the complete fix for the "Unknown action" error 
when users click "Upload Payment Proof" in the Telegram bot.

WHAT WAS FIXED:
- Added missing callback handler for upload_payment_ callbacks
- Created handle_upload_payment_proof() function
- Enhanced photo handler to process payment proofs properly
- Added admin notification system with approve/reject buttons

APPLY THIS FIX TO YOUR BOT:
1. Add the new function handle_upload_payment_proof()
2. Add the callback handler case in handle_callback_query()
3. Update the photo handler to process payment proofs
4. Restart your bot

Author: AI Assistant
Date: 2024
"""

# Imports (these will be available in your main bot file)
# from datetime import datetime
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ContextTypes

try:
    from datetime import datetime
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
except ImportError:
    # This script is meant to be a template, imports are optional for viewing
    print("Note: This is a template script. Telegram imports not needed for viewing instructions.")

# =============================================================================
# NEW FUNCTION: Handle Upload Payment Proof
# =============================================================================

async def handle_upload_payment_proof(update, context, booking_id):
    """
    Handle the upload payment proof button click.
    Sets user state to expect payment proof photo upload.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id

    # Check if booking exists
    # Note: bookings, user_states, pending_payments, ADMIN_IDS, ADMIN_USERNAME, create_inline_keyboard 
    # are global variables that should exist in your main bot file
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

# =============================================================================
# CALLBACK HANDLER UPDATE
# =============================================================================

def add_upload_payment_callback_handler():
    """
    Add this case to your handle_callback_query function.
    
    Insert this BEFORE the 'else:' clause that shows "Unknown action":
    """
    callback_code = '''
        elif data.startswith('upload_payment_'):
            booking_id = data.split('_')[2]
            await handle_upload_payment_proof(update, context, booking_id)
    '''
    return callback_code

# =============================================================================
# PHOTO HANDLER UPDATE
# =============================================================================

async def enhanced_photo_handler_payment_proof_section(update, context):
    """
    Enhanced photo handler section for payment proof processing.
    
    Add this to your handle_photo() function in the 'else:' section
    (after teacher editing states but before generic photo handling).
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
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

# =============================================================================
# INSTALLATION INSTRUCTIONS
# =============================================================================

def installation_instructions():
    """
    Step-by-step instructions to apply this fix to your bot.
    """
    instructions = """
    INSTALLATION INSTRUCTIONS:
    =========================
    
    1. ADD NEW FUNCTION:
       - Copy the handle_upload_payment_proof() function above
       - Add it to your hard.py file (after handle_reject_payment function)
    
    2. UPDATE CALLBACK HANDLER:
       - In your handle_callback_query() function
       - Add this case BEFORE the final 'else:' clause:
       
       elif data.startswith('upload_payment_'):
           booking_id = data.split('_')[2]
           await handle_upload_payment_proof(update, context, booking_id)
    
    3. UPDATE PHOTO HANDLER:
       - In your handle_photo() function
       - In the final 'else:' section, add the payment proof processing code
       - Replace the simple "Payment proof received" message with the enhanced handler
    
    4. RESTART BOT:
       - Stop your current bot
       - Run: python3 hard.py
    
    TESTING:
    ========
    1. Create a booking
    2. Click "Upload Payment Proof" button
    3. Should show upload instructions (not "Unknown action")
    4. Send a photo
    5. Should confirm receipt and notify admin
    
    FEATURES ADDED:
    ==============
    ✅ Proper handling of "Upload Payment Proof" clicks
    ✅ User state management for photo uploads
    ✅ Automatic payment proof processing
    ✅ Admin notifications with approve/reject buttons
    ✅ User feedback and confirmation messages
    ✅ Booking status updates
    ✅ Security checks (user can only upload for own bookings)
    """
    return instructions

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("🔧 TELEGRAM BOT PAYMENT PROOF UPLOAD FIX")
    print("=" * 50)
    print(installation_instructions())
    print("\n✅ This script contains all the code needed to fix the payment proof upload issue!")
    print("📁 Copy the functions above into your bot code and follow the installation instructions.")