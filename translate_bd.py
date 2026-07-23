import re

with open('static/js/bd_locations.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Dictionary for translations
translations = {
    'Barishal': 'বরিশাল', 'Chattogram': 'চট্টগ্রাম', 'Dhaka': 'ঢাকা', 'Khulna': 'খুলনা',
    'Mymensingh': 'ময়মনসিংহ', 'Rajshahi': 'রাজশাহী', 'Rangpur': 'রংপুর', 'Sylhet': 'সিলেট',
    'Barguna': 'বরগুনা', 'Bhola': 'ভোলা', 'Jhalokati': 'ঝালকাঠি', 'Patuakhali': 'পটুয়াখালী', 'Pirojpur': 'পিরোজপুর',
    'Bandarban': 'বান্দরবান', 'Brahmanbaria': 'ব্রাহ্মণবাড়িয়া', 'Chandpur': 'চাঁদপুর', 'Cox\'s Bazar': 'কক্সবাজার',
    'Feni': 'ফেনী', 'Khagrachhari': 'খাগড়াছড়ি', 'Lakshmipur': 'লক্ষ্মীপুর', 'Noakhali': 'নোয়াখালী', 'Rangamati': 'রাঙ্গামাটি',
    'Faridpur': 'ফরিদপুর', 'Gazipur': 'গাজীপুর', 'Gopalganj': 'গোপালগঞ্জ', 'Kishoreganj': 'কিশোরগঞ্জ', 'Madaripur': 'মাদারীপুর',
    'Manikganj': 'মানিকগঞ্জ', 'Munshiganj': 'মুন্সীগঞ্জ', 'Narayanganj': 'নারায়ণগঞ্জ', 'Narsingdi': 'নরসিংদী', 'Rajbari': 'রাজবাড়ী',
    'Shariatpur': 'শরীয়তপুর', 'Tangail': 'টাঙ্গাইল',
    'Bagerhat': 'বাগেরহাট', 'Chuadanga': 'চুয়াডাঙ্গা', 'Jashore': 'যশোর', 'Jhenaidah': 'ঝিনাইদহ', 'Kushtia': 'কুষ্টিয়া',
    'Magura': 'মাগুরা', 'Meherpur': 'মেহেরপুর', 'Narail': 'নড়াইল', 'Satkhira': 'সাতক্ষীরা',
    'Jamalpur': 'জামালপুর', 'Netrokona': 'নেত্রকোনা', 'Sherpur': 'শেরপুর',
    'Bogra': 'বগুড়া', 'Joypurhat': 'জয়পুরহাট', 'Naogaon': 'নওগাঁ', 'Natore': 'নাটোর', 'Chapainawabganj': 'চাঁপাইনবাবগঞ্জ',
    'Pabna': 'পাবনা', 'Sirajganj': 'সিরাজগঞ্জ',
    'Dinajpur': 'দিনাজপুর', 'Gaibandha': 'গাইবান্ধা', 'Kurigram': 'কুড়িগ্রাম', 'Lalmonirhat': 'লালমনিরহাট', 'Nilphamari': 'নীলফামারী',
    'Panchagarh': 'পঞ্চগড়', 'Thakurgaon': 'ঠাকুরগাঁও',
    'Habiganj': 'হবিগঞ্জ', 'Moulvibazar': 'মৌলভীবাজার', 'Sunamganj': 'সুনামগঞ্জ'
}

# Replace divisions and districts (keys and array elements that match)
# Only replace keys if they match exactly to avoid double translations
for eng, ban in translations.items():
    # Replace JSON keys "English"
    text = re.sub(rf'\"({eng})\"', f'\"{ban} ({eng})\"', text)

with open('static/js/bd_locations.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done!')
