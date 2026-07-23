const bdLocations = {
  "বরিশাল (Barishal)": {
    "বরগুনা (Barguna)": ["আমতলী (Amtali)", "বামনা (Bamna)", "বরগুনা সদর (Barguna Sadar)", "বেতাগী (Betagi)", "পাথরঘাটা (Patharghata)", "তালতলী (Taltali)"],
    "বরিশাল (Barishal)": ["আগৈলঝাড়া (Agailjhara)", "বাবুগঞ্জ (Babuganj)", "বাকেরগঞ্জ (Bakerganj)", "বানারীপাড়া (Banaripara)", "গৌরনদী (Gaurnadi)", "হিজলা (Hizla)", "বরিশাল সদর (Barishal Sadar)", "মেহেন্দিগঞ্জ (Mehendiganj)", "মুলাদী (Muladi)", "উজিরপুর (Wazirpur)"],
    "ভোলা (Bhola)": ["ভোলা সদর (Bhola Sadar)", "বোরহানউদ্দিন (Burhanuddin)", "চরফ্যাশন (Char Fasson)", "দৌলতখান (Daulatkhan)", "লালমোহন (Lalmohan)", "মনপুরা (Manpura)", "তাজুমুদ্দিন (Tazumuddin)"],
    "ঝালকাঠি (Jhalokati)": ["ঝালকাঠি সদর (Jhalokati Sadar)", "কাঠালিয়া (Kathalia)", "নলছিটি (Nalchity)", "রাজাপুর (Rajapur)"],
    "পটুয়াখালী (Patuakhali)": ["বাউফল (Bauphal)", "দশমিনা (Dashmina)", "গলাচিপা (Galachipa)", "কলাপাড়া (Kalapara)", "মির্জাগঞ্জ (Mirzaganj)", "পটুয়াখালী সদর (Patuakhali Sadar)", "রাঙ্গাবালী (Rangabali)", "ডুমকি (Dumki)"],
    "পিরোজপুর (Pirojpur)": ["ভান্ডারিয়া (Bhandaria)", "কাউখালী (Kawkhali)", "মঠবাড়িয়া (Mathbaria)", "নাজিরপুর (Nazirpur)", "পিরোজপুর সদর (Pirojpur Sadar)", "নেছারাবাদ (স্বরূপকাঠি) (Nesarabad Swarupkati)", "ইন্দুরকানী (Indurkani)"]
  },
  "চট্টগ্রাম (Chattogram)": {
    "বান্দরবান (Bandarban)": ["আলীকদম (Ali Kadam)", "বান্দরবান সদর (Bandarban Sadar)", "লামা (Lama)", "নাইক্ষ্যংছড়ি (Naikhongchhari)", "রোয়াংছড়ি (Rowangchhari)", "রুমা (Ruma)", "থানচি (Thanchi)"],
    "ব্রাহ্মণবাড়িয়া (Brahmanbaria)": ["আখাউড়া (Akhaura)", "বাঞ্ছারামপুর (Bancharampur)", "ব্রাহ্মণবাড়িয়া সদর (Brahmanbaria Sadar)", "কসবা (Kasba)", "নবীনগর (Nabinagar)", "নাসিরনগর (Nasirnagar)", "সরাইল (Sarail)", "আশুগঞ্জ (Ashuganj)", "বিজয়নগর (Bijoynagar)"],
    "চাঁদপুর (Chandpur)": ["চাঁদপুর সদর (Chandpur Sadar)", "ফরিদগঞ্জ (Faridganj)", "হাইমচর (Haimchar)", "হাজীগঞ্জ (Haziganj)", "কচুয়া (Kachua)", "মতলব দক্ষিণ (Matlab Dakshin)", "মতলব উত্তর (Matlab Uttar)", "শাহরাস্তি (Shahrasti)"],
    "চট্টগ্রাম (Chattogram)": ["আনোয়ারা (Anwara)", "বাঁশখালী (Banshkhali)", "বোয়ালখালী (Boalkhali)", "চন্দনাইশ (Chandanaish)", "ডবলমুরিং (Double Mooring)", "ফটিকছড়ি (Fatikchhari)", "হাটহাজারী (Hathazari)", "লোহাগাড়া (Lohagara)", "মিরসরাই (Mirsharai)", "পটিয়া (Patiya)", "রাঙ্গুনিয়া (Rangunia)", "রাউজান (Raozan)", "সন্দ্বীপ (Sandwip)", "সাতকানিয়া (Satkania)", "সীতাকুণ্ড (Sitakunda)", "চকবাজার (Chawkbazar)", "কোতোয়ালী (Kotwali)", "পাঁচলাইশ (Panchlaish)", "হালিশহর (Halishahar)", "পাহাড়তলী (Pahartali)", "বন্দর (Bandar)"],
    "কক্সবাজার (Cox's Bazar)": ["চকোরিয়া (Chakaria)", "কক্সবাজার সদর (Cox's Bazar Sadar)", "কুতুবদিয়া (Kutubdia)", "মহেশখালী (Maheshkhali)", "রামু (Ramu)", "টেকনাফ (Teknaf)", "উখিয়া (Ukhia)", "পেকুয়া (Pekua)"],
    "ফেনী (Feni)": ["ছাগলনাইয়া (Chhagalnaiya)", "দাগনভূঞা (Daganbhuiyan)", "ফেনী সদর (Feni Sadar)", "পরশুরাম (Parshuram)", "সোনাগাজী (Sonagazi)", "ফুলগাজী (Fulgazi)"],
    "খাগড়াছড়ি (Khagrachhari)": ["দিঘীনালা (Dighinala)", "খাগড়াছড়ি সদর (Khagrachhari Sadar)", "লক্ষ্মীছড়ি (Lakshmichhari)", "মহালছড়ি (Mahalchhari)", "মানিকছড়ি (Manikchhari)", "মাটিরাঙ্গা (Matiranga)", "পানছড়ি (Panchhari)", "রামগড় (Ramgarh)"],
    "লক্ষ্মীপুর (Lakshmipur)": ["লক্ষ্মীপুর সদর (Lakshmipur Sadar)", "রায়পুর (Raipur)", "রামগঞ্জ (Ramganj)", "রামগতি (Ramgati)", "কমলনগর (Kamalnagar)"],
    "নোয়াখালী (Noakhali)": ["বেগমগঞ্জ (Begumganj)", "নোয়াখালী সদর (Noakhali Sadar)", "চাটখিল (Chatkhil)", "কোম্পানীগঞ্জ (Companiganj)", "হাতিয়া (Hatiya)", "সেনবাগ (Senbagh)", "সোনাইমুড়ী (Sonaimuri)", "সুবর্ণচর (Subarnachar)", "কবিরহাট (Kabirhat)"],
    "রাঙ্গামাটি (Rangamati)": ["বাঘাইছড়ি (Bagaichhari)", "বরকল (Barkal)", "কাউখালী (Kawkhali)", "বিলাইছড়ি (Belaichhari)", "কাপ্তাই (Kaptai)", "জুরাছড়ি (Juraichhari)", "লংগদু (Langadu)", "নানিয়ারচর (Naniarchar)", "রাজস্থলী (Rajasthali)", "রাঙ্গামাটি সদর (Rangamati Sadar)"]
  },
  "ঢাকা (Dhaka)": {
    "ঢাকা (Dhaka)": ["ধামরাই (Dhamrai)", "দোহার (Dohar)", "কেরানীগঞ্জ (Keraniganj)", "নবাবগঞ্জ (Nawabganj)", "সাভার (Savar)", "মিরপুর (Mirpur)", "মোহাম্মদপুর (Mohammadpur)", "ধানমন্ডি (Dhanmondi)", "গুলশান (Gulshan)", "উত্তরা (Uttara)", "তেজগাঁও (Tejgaon)", "রমনা (Ramna)", "মতিঝিল (Motijheel)", "পল্টন (Paltan)", "বাড্ডা (Badda)", "খিলগাঁও (Khilgaon)", "যাত্রাবাড়ী (Jatrabari)", "ডেমরা (Demra)", "ক্যান্টনমেন্ট (Cantonment)", "কাফরুল (Kafrul)", "শাহবাগ (Shahbagh)", "হাজারীবাগ (Hazaribagh)", "লালবাগ (Lalbagh)", "কামরাঙ্গীরচর (Kamrangirchar)"],
    "ফরিদপুর (Faridpur)": ["আলফাডাঙা (Alfadanga)", "ভাঙ্গা (Bhanga)", "বোয়ালমারী (Boalmari)", "চরভদ্রাসন (Charbhadrasan)", "ফরিদপুর সদর (Faridpur Sadar)", "মধুখালী (Madhukhali)", "নগরকান্দা (Nagarkanda)", "সদরপুর (Sadarpur)", "সালথা (Saltha)"],
    "গাজীপুর (Gazipur)": ["গাজীপুর সদর (Gazipur Sadar)", "কালিয়াকৈর (Kaliakair)", "কালীগঞ্জ (Kaliganj)", "কাপাসিয়া (Kapasia)", "শ্রীপুর (Sreepur)"],
    "গোপালগঞ্জ (Gopalganj)": ["গোপালগঞ্জ সদর (Gopalganj Sadar)", "কাশিয়ানী (Kashiani)", "কোটালীপাড়া (Kotalipara)", "মুকসুদপুর (Muksudpur)", "টুঙ্গিপাড়া (Tungipara)"],
    "কিশোরগঞ্জ (Kishoreganj)": ["অষ্টগ্রাম (Astagram)", "বাজিতপুর (Bajitpur)", "ভৈরব (Bhairab)", "হোসেনপুর (Hossainpur)", "ইটনা (Itna)", "করিমগঞ্জ (Karimganj)", "কটিয়াদী (Katiadi)", "কিশোরগঞ্জ সদর (Kishoreganj Sadar)", "কুলিয়ারচর (Kuliarchar)", "মিঠামইন (Mithamain)", "নিকলী (Nikli)", "পাকুন্দিয়া (Pakundia)", "তাড়াইল (Tarail)"],
    "মাদারীপুর (Madaripur)": ["রাজৈর (Rajoir)", "মাদারীপুর সদর (Madaripur Sadar)", "কালকিনি (Kalkini)", "শিবচর (Shibchar)"],
    "মানিকগঞ্জ (Manikganj)": ["দৌলতপুর (Daulatpur)", "ঘিওর (Ghior)", "হরিরামপুর (Harirampur)", "মানিকগঞ্জ সদর (Manikganj Sadar)", "সাটুরিয়া (Saturia)", "শিবালয় (Shivalaya)", "সিঙ্গাইর (Singair)"],
    "মুন্সীগঞ্জ (Munshiganj)": ["বাড়িঝাট (Barijhat)", "গজারিয়া (Gazaria)", "লৌহজং (Lohajang)", "মুন্সীগঞ্জ সদর (Munshiganj Sadar)", "সিরাজদিখান (Sirajdikhan)", "শ্রীনগর (Sreenagar)", "টংগীবাড়ী (Tongibari)"],
    "নারায়ণগঞ্জ (Narayanganj)": ["আড়াইহাজার (Araihazar)", "বন্দর (Bandar)", "নারায়ণগঞ্জ সদর (Narayanganj Sadar)", "রূপগঞ্জ (Rupganj)", "সোনারগাঁ (Sonargaon)"],
    "নরসিংদী (Narsingdi)": ["নরসিংদী সদর (Narsingdi Sadar)", "বেলাবো (Belabo)", "মনোহরদী (Monohardi)", "পলাশ (Palash)", "রায়পুরা (Raipura)", "শিবপুর (Shibpur)"],
    "রাজবাড়ী (Rajbari)": ["বালিয়াকান্দি (Baliakandi)", "গোয়ালন্দ ঘাট (Goalanda Ghat)", "পাংশা (Pangsha)", "রাজবাড়ী সদর (Rajbari Sadar)", "কালুখালী (Kalukhali)"],
    "শরীয়তপুর (Shariatpur)": ["ভেদরগঞ্জ (Bhedarganj)", "ডামুড্যা (Damudya)", "গোসাইরহাট (Gosairhat)", "নড়িয়া (Naria)", "শরীয়তপুর সদর (Shariatpur Sadar)", "জাজিরা (Zajira)"],
    "টাঙ্গাইল (Tangail)": ["গোপালপুর (Gopalpur)", "বাসাইল (Basail)", "ভুয়াপুর (Bhuapur)", "দেলদুয়ার (Delduar)", "ঘাটাইল (Ghatail)", "কালিহাতী (Kalihati)", "মধুপুর (Madhupur)", "মির্জাপুর (Mirzapur)", "নাগরপুর (Nagarpur)", "সখিপুর (Sakhipur)", "টাঙ্গাইল সদর (Tangail Sadar)", "ধনবাড়ী (Dhanbari)"]
  },
  "খুলনা (Khulna)": {
    "বাগেরহাট (Bagerhat)": ["বাগেরহাট সদর (Bagerhat Sadar)", "চিতলমারী (Chitalmari)", "ফকিরহাট (Fakirhat)", "কচুয়া (Kachua)", "মোল্লাহাট (Mollahat)", "মংলা (Mongla)", "মোড়েলগঞ্জ (Morrelganj)", "রামপাল (Rampal)", "শরণখোলা (Sarankhola)"],
    "চুয়াডাঙ্গা (Chuadanga)": ["আলমডাঙ্গা (Alamdanga)", "চুয়াডাঙ্গা সদর (Chuadanga Sadar)", "দামুড়হুদা (Damurhuda)", "জীবননগর (Jibannagar)"],
    "যশোর (Jashore)": ["অভয়নগর (Abhaynagar)", "বাঘারপাড়া (Bagherpara)", "চৌগাছা (Chowgacha)", "যশোর সদর (Jashore Sadar)", "ঝিকরগাছা (Jhikargacha)", "কেশবপুর (Keshabpur)", "মনিরামপুর (Manirampur)", "শার্শা (Sharsha)"],
    "ঝিনাইদহ (Jhenaidah)": ["হরিণাকুণ্ডু (Harinakunda)", "ঝিনাইদহ সদর (Jhenaidah Sadar)", "কালীগঞ্জ (Kaliganj)", "কোটচাঁদপুর (Kotchandpur)", "মহেশপুর (Maheshpur)", "শৈলকুপা (Shailkupa)"],
    "খুলনা (Khulna)": ["বটিয়াঘাটা (Batiaghata)", "দাকোপ (Dacope)", "ডুমুরিয়া (Dumuria)", "দিঘলিয়া (Digholia)", "কয়রা (Koyra)", "পাইকগাছা (Paikgachha)", "ফুলতলা (Phultala)", "রূপসা (Rupsha)", "তেরখাদা (Terokhada)"],
    "কুষ্টিয়া (Kushtia)": ["ভেড়ামারা (Bheramara)", "দৌলতপুর (Daulatpur)", "খোকসা (Khoksa)", "কুমারখালী (Kumarkhali)", "কুষ্টিয়া সদর (Kushtia Sadar)", "মিরপুর (Mirpur)"],
    "মাগুরা (Magura)": ["মাগুরা সদর (Magura Sadar)", "মোহাম্মদপুর (Mohammadpur)", "শালিখা (Shalikha)", "শ্রীপুর (Sreepur)"],
    "মেহেরপুর (Meherpur)": ["গাংনী (Gangni)", "মেহেরপুর সদর (Meherpur Sadar)", "মুজিবনগর (Mujibnagar)"],
    "নড়াইল (Narail)": ["কালিয়া (Kalia)", "লোহাগাড়া (Lohagara)", "নড়াইল সদর (Narail Sadar)"],
    "সাতক্ষীরা (Satkhira)": ["আশাশুনি (Assasuni)", "দেবহাটা (Debhata)", "কলারোয়া (Kalaroa)", "কালীগঞ্জ (Kaliganj)", "সাতক্ষীরা সদর (Satkhira Sadar)", "শ্যামনগর (Shyamnagar)", "তালা (Tala)"]
  },
  "ময়মনসিংহ (Mymensingh)": {
    "জামালপুর (Jamalpur)": ["বকশীগঞ্জ (Baksiganj)", "দেওয়ানগঞ্জ (Dewanganj)", "ইসলামপুর (Islampur)", "জামালপুর সদর (Jamalpur Sadar)", "মাদারগঞ্জ (Madarganj)", "মেলান্দহ (Melandaha)", "সরিষাবাড়ী (Sarishabari)"],
    "ময়মনসিংহ (Mymensingh)": ["ভালুকা (Bhaluka)", "ধোবাউড়া (Dhobaura)", "ফুলবাড়ীয়া (Fulbaria)", "গফরগাঁও (Gaffargaon)", "গৌরীপুর (Gauripur)", "হালুয়াঘাট (Haluaghat)", "ঈশ্বরগঞ্জ (Ishwarganj)", "ময়মনসিংহ সদর (Mymensingh Sadar)", "মুক্তাগাছা (Muktagachha)", "নান্দাইল (Nandail)", "ফুলপুর (Phulpur)", "ত্রিশাল (Trishal)", "তারাকান্দা (Tara Khanda)"],
    "নেত্রকোনা (Netrokona)": ["আটপাড়া (Atpara)", "বারহাট্টা (Barhatta)", "দুর্গাপুর (Durgapur)", "খালিয়াজুরী (Khaliajuri)", "কলমাকান্দা (Kalmakanda)", "কেন্দুয়া (Kendua)", "মদন (Madan)", "মোহনগঞ্জ (Mohanganj)", "নেত্রকোনা সদর (Netrokona Sadar)", "পূর্বধলা (Purbadhala)"],
    "শেরপুর (Sherpur)": ["ঝিনাইগাতী (Jhenaigati)", "নকলা (Nakla)", "নালিতাবাড়ী (Nalitabari)", "শেরপুর সদর (Sherpur Sadar)", "শ্রীবরদী (Sreebardi)"]
  },
  "রাজশাহী (Rajshahi)": {
    "বগুড়া (Bogra)": ["আদমদীঘি (Adamdighi)", "বগুড়া সদর (Bogra Sadar)", "ধুনট (Dhunat)", "দুপচাঁচিয়া (Dhupchanchia)", "গাবতলী (Gabtali)", "কাহালু (Kahaloo)", "নন্দীগ্রাম (Nandigram)", "সারিয়াকান্দি (Sariakandi)", "শেরপুর (Sherpur)", "শিবগঞ্জ (Shibganj)", "সোনাতলা (Sonatola)", "শাহজাহানপুর (Shajahanpur)"],
    "জয়পুরহাট (Joypurhat)": ["আক্কেলপুর (Akkelpur)", "জয়পুরহাট সদর (Joypurhat Sadar)", "কালাই (Kalai)", "ক্ষেতলাল (Khetlal)", "পাঁচবিবি (Panchbibi)"],
    "নওগাঁ (Naogaon)": ["আত্রাই (Atrai)", "বদলগাছী (Badalgachhi)", "ধামইরহাট (Dhamoirhat)", "মান্দা (Manda)", "মহাদেবপুর (Mahadebpur)", "নওগাঁ সদর (Naogaon Sadar)", "নিয়ামাতপুর (Niamatpur)", "পত্নীতলা (Patnitala)", "পোরশা (Porsha)", "রাণীনগর (Raninagar)", "সাপাহার (Sapahar)"],
    "নাটোর (Natore)": ["বাগাতিপাড়া (Bagatipara)", "বড়াইগ্রাম (Baraigram)", "গুরুদাসপুর (Gurudaspur)", "লালপুর (Lalpur)", "নাটোর সদর (Natore Sadar)", "সিংড়া (Singra)", "নলডাঙ্গা (Naldanga)"],
    "চাঁপাইনবাবগঞ্জ (Chapainawabganj)": ["ভোলাহাট (Bholahat)", "গোমস্তাপুর (Gomastapur)", "নাচোল (Nachole)", "চাঁপাইনবাবগঞ্জ সদর (Chapainawabganj Sadar)", "শিবগঞ্জ (Shibganj)"],
    "পাবনা (Pabna)": ["আটঘরিয়া (Atgharia)", "বেড়া (Bera)", "ভাংগুড়া (Bhangura)", "চাটমোহর (Chatmohar)", "ফরিদপুর (Faridpur)", "ঈশ্বরদী (Ishwardi)", "পাবনা সদর (Pabna Sadar)", "সাঁথিয়া (Santhia)", "সুজানগর (Sujanagar)"],
    "রাজশাহী (Rajshahi)": ["বাঘা (Bagha)", "বাগমারা (Bagmara)", "চারঘাট (Charghat)", "দুর্গাপুর (Durgapur)", "গোদাগাড়ী (Godagari)", "মোহনপুর (Mohanpur)", "পবা (Paba)", "পুঠিয়া (Puthia)", "তানোর (Tanore)"],
    "সিরাজগঞ্জ (Sirajganj)": ["বেলকুচি (Belkuchi)", "চৌহালী (Chauhali)", "কামারখন্দ (Kamarkhanda)", "কাজীপুর (Kazipur)", "রায়গঞ্জ (Rayganj)", "শাহজাদপুর (Shahjadpur)", "সিরাজগঞ্জ সদর (Sirajganj Sadar)", "তাড়াশ (Tarash)", "উল্লাপাড়া (Ullahpara)"]
  },
  "রংপুর (Rangpur)": {
    "দিনাজপুর (Dinajpur)": ["বিরামপুর (Birampur)", "বীরগঞ্জ (Birganj)", "বিরল (Biral)", "বোচাগঞ্জ (Bochaganj)", "চিরিরবন্দর (Chirirbandar)", "ফুলবাড়ী (Phulbari)", "ঘোড়াঘাট (Ghoraghat)", "হাকিমপুর (Hakimpur)", "কাহারোল (Kaharole)", "খানসামা (Khansama)", "দিনাজপুর সদর (Dinajpur Sadar)", "নবাবগঞ্জ (Nawabganj)", "পার্বতীপুর (Parbatipur)"],
    "গাইবান্ধা (Gaibandha)": ["গাইবান্ধা সদর (Gaibandha Sadar)", "সাদুল্লাপুর (Sadullapur)", "পলাশবাড়ী (Palashbari)", "সুন্দরগঞ্জ (Sundarganj)", "সাঘাটা (Saghata)", "গোবিন্দগঞ্জ (Gobindaganj)", "ফুলছড়ি (Phulchhari)"],
    "কুড়িগ্রাম (Kurigram)": ["ভূরুঙ্গামারী (Bhurungamari)", "চিলমারী (Chilmari)", "ফুলবাড়ী (Phulbari)", "কুড়িগ্রাম সদর (Kurigram Sadar)", "নাগেশ্বরী (Nageshwari)", "রাজারহাট (Rajarhat)", "চর রাজিবপুর (Rajibpur)", "রৌমারী (Rowmari)", "উলিপুর (Ulipur)"],
    "লালমনিরহাট (Lalmonirhat)": ["আদিতমারী (Aditmari)", "হাতীবান্ধা (Hatibandha)", "কালীগঞ্জ (Kaliganj)", "লালমনিরহাট সদর (Lalmonirhat Sadar)", "পাটগ্রাম (Patgram)"],
    "নীলফামারী (Nilphamari)": ["ডিমলা (Dimla)", "ডোমার (Domar)", "জলঢাকা (Jaldhaka)", "কিশোরগঞ্জ (Kishoreganj)", "নীলফামারী সদর (Nilphamari Sadar)", "সৈয়দপুর (Saidpur)"],
    "পঞ্চগড় (Panchagarh)": ["আটোয়ারী (Atwari)", "বোদা (Boda)", "দেবীগঞ্জ (Debiganj)", "পঞ্চগড় সদর (Panchagarh Sadar)", "তেঁতুলিয়া (Tetulia)"],
    "রংপুর (Rangpur)": ["বদরগঞ্জ (Badarganj)", "গংগাচড়া (Gangachara)", "কাউনিয়া (Kaunia)", "রংপুর সদর (Rangpur Sadar)", "মিঠাপুকুর (Mithapukur)", "পীরগাছা (Pirgachha)", "পীরগঞ্জ (Pirganj)", "তারাগঞ্জ (Taraganj)"],
    "ঠাকুরগাঁও (Thakurgaon)": ["বালিয়াডাংগী (Baliadangi)", "হরিপুর (Haripur)", "রাণীশংকৈল (Ranisankail)", "ঠাকুরগাঁও সদর (Thakurgaon Sadar)", "পীরগঞ্জ (Pirganj)"]
  },
  "সিলেট (Sylhet)": {
    "হবিগঞ্জ (Habiganj)": ["আজমিরীগঞ্জ (Ajmiriganj)", "বাহুবল (Bahubal)", "বানিয়াচং (Baniyachong)", "চুনারুঘাট (Chunarughat)", "হবিগঞ্জ সদর (Habiganj Sadar)", "লাখাই (Lakhai)", "মাধবপুর (Madhabpur)", "নবীগঞ্জ (Nabiganj)", "শায়েস্তাগঞ্জ (Sayestaganj)"],
    "মৌলভীবাজার (Moulvibazar)": ["বড়লেখা (Barlekha)", "কমলগঞ্জ (Kamalganj)", "কুলাউড়া (Kulaura)", "মৌলভীবাজার সদর (Moulvibazar Sadar)", "রাজনগর (Rajnagar)", "শ্রীমঙ্গল (Sreemangal)", "জুড়ী (Juri)"],
    "সুনামগঞ্জ (Sunamganj)": ["বিশ্বম্ভরপুর (Bishwamambarpur)", "ছাতক (Chhatak)", "দিরাই (Derai)", "ধর্মপাশা (Dharamapasha)", "দোয়ারাবাজার (Dowarabazar)", "জগন্নাথপুর (Jagannathpur)", "জামালগঞ্জ (Jamalganj)", "শাল্লা (Sullah)", "সুনামগঞ্জ সদর (Sunamganj Sadar)", "তাহিরপুর (Tahirpur)", "শান্তিগঞ্জ (Shantiganj)"],
    "সিলেট (Sylhet)": ["বালাগঞ্জ (Balaganj)", "বিয়ানীবাজার (Beanibazar)", "বিশ্বনাথ (Bishwanath)", "কোম্পানীগঞ্জ (Companiganj)", "ফেঞ্চুগঞ্জ (Fenchuganj)", "গোলাপগঞ্জ (Golapganj)", "গোয়াইনঘাট (Gowainghat)", "জৈন্তাপুর (Jaintiapur)", "কানাইঘাট (Kanaighat)", "সিলেট সদর (Sylhet Sadar)", "জকিগঞ্জ (Zakiganj)", "দক্ষিণ সুরমা (Dakshin Surma)", "ওসমানীনগর (Osmaninagar)"]
  }
};
