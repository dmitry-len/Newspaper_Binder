import os
import cv2
import re
import pytesseract
from PIL import Image

# Путь к папке с изображениями
questionable_folder = os.path.join(os.getcwd(), 'Doubtful\\')
unreadable = os.path.join(os.getcwd(), 'unreadable\\')
images_folder = "gazeta\\"
template1 = cv2.imread('template11.jpg',cv2.IMREAD_GRAYSCALE)
template2 = cv2.imread('template22.jpg',cv2.IMREAD_GRAYSCALE)

# Путь к исполняемому файлу Tesseract
pytesseract.pytesseract.tesseract_cmd = "tesseract\\tesseract.exe"

threshold = 0.363

# Инициализация переменных
current_issue_number = None
current_issue_pages = []
current_issue_order_number = None
current_issue_month = None
current_issue_day = None
current_issue_year = None
saved_issue_number_match = None
saved_order_number_match = None
saved_month_match = None
saved_day_match = None
saved_year_match = None
output_filename = None
total_attempts = 3
attempt = 0
rescaling = 0
rescaling_coef = 5
i=0
n=0

month_dict = {
	"июн": "июня",
	"июл": "июля",
	"мар": "марта",
	"ян": "января",
	"фе": "февраля",
	"ап": "апреля",
	"ав": "августа",
	"се": "сентября",
	"ок": "октября",
	"но": "ноября",
	"де": "декабря",
	"ма": "мая",
}

# Паттерны для поиска номера выпуска газеты, порядкового номера выпуска, даты и года выпуска
issue_number_pattern = r"(?:№\s*)?([0-9][0-9]?[0-9]?)(?=\s*\(|$)|№([0-9][0-9]?[0-9]?)"
order_number_pattern = r'[(]\s*?([0-9]\s*?){5}'
day_pattern = r'(?<!№|=|\()(?:(?<=\s)|(?<=\n)|(?<=\r\n))\s*?(?<![0-9])([12]\s*?\d|3\s*?[01]|[1-9])\b\s*?(?!\s*?[\(<>\\/.,+-=?!\)"№;%"]| \s*?г\.|\s*?год)'
month_pattern = r"(?i)\b(" + "|".join(month_dict.keys()) + r")[а-яёЮюИи]*\b"
year_pattern = r"(?<!\()\b(2\s*?0\s*?[0-2]\s*?\d|2\s*?0\s*?2\s*?3)\b(?!\))"

def textGenerate(matched_area,h,w,hw,psm):
	config = (f'-l rus --oem 2 --psm {psm}')
	new_height, new_width = h * hw, w * hw
	try:
		resized_img = cv2.resize(matched_area, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
	except:
		print(f"Не удалось изменить размер изображения \n{matched_area.shape}\n")
		resized_img = cv2.resize(matched_area, (1, 1), interpolation=cv2.INTER_CUBIC)

	ret, thresh = cv2.threshold(resized_img, 127, 255, cv2.THRESH_BINARY)
	contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
	# Фильтрация контуров для поиска текстовых областей
	text_contours = []

	# for contour in contours:
	# 	x, y, w, h = cv2.boundingRect(contour)
	# 	area = cv2.contourArea(contour)
	# 	if area > 50 and w > 10 and h > 10:
	# 		text_contours.append(contour)

	# Выравнивание текста
	for contour in text_contours:
		x, y, w, h = cv2.boundingRect(contour)
		roi = resized_img[y:y+h, x:x+w]
		_, roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		rows, cols = roi.shape
		if rows > cols:
			M = cv2.getRotationMatrix2D((cols/2, rows/2), 90, 1)
			roi = cv2.warpAffine(roi, M, (cols, rows))
	# Обнаружение текста на изображении
	text = pytesseract.image_to_string(resized_img, config=config)
	text = "\n\n---------------ТЕКСТ ХВ={hw} ПСМ={psm}---------------\n\n{replace_text}\n\n----------------------------------------------------".format(hw=hw, psm=psm, replace_text=text.replace('\n', ' '))
	return text

def comparison(template, img):
	
	# метод matchTemplate() для поиска шаблонного изображения в исходном изображении
	result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)

	# Получите координаты найденного шаблона
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

	h, w = template.shape[:2]
	top_left = max_loc
	bottom_right = (top_left[0] + w, top_left[1] + h)

	return h, w, top_left, bottom_right, max_val, max_loc

def variables(img):
	templates = [template1, template2]
	info_templates = [comparison(template, img) for template in templates]
	h, w, top_left, bottom_right, max_val, max_loc = max(info_templates, key=lambda x: x[4])
	return h, w, top_left, bottom_right, max_val, max_loc

def recog(image_filename):
	global current_issue_number
	global current_issue_pages
	global current_issue_order_number
	global current_issue_day_month
	global current_issue_year
	global output_filename
	global n
	global saved_issue_number_match
	global saved_order_number_match
	global saved_month_match
	global saved_day_match
	global saved_year_match

	if image_filename.endswith(".jpg") or image_filename.endswith(".jpeg"):
		recognized = False
		probably_recognizable = False
		Matches = False
		# Получение полного пути к изображению
		image_path = os.path.join(images_folder, image_filename)
		# Загрузка изображения
		img = cv2.imread(image_path,cv2.IMREAD_GRAYSCALE)

		h, w, top_left, bottom_right, max_val, max_loc = variables(img)

		print(f"Соответствие {max_val}")
		if max_val > threshold:
			Matches = True
			
			matched_area = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

			if attempt > 0:
				try:
				    matched_area = img[max(0, top_left[1]-rescaling):bottom_right[1]+rescaling, max(0, top_left[0]-rescaling):bottom_right[0]+rescaling]
				except cv2.error as e:
				    print("Ошибка во время увеличения области распознавания ", e)
				
			text = textGenerate(matched_area,h,w,2,11) + textGenerate(matched_area,h,w,2,12) + textGenerate(matched_area,h,w,4,12) + textGenerate(matched_area,h,w,4,6) + textGenerate(matched_area,h,w,4,11)
		
			print(text)

			result_dict = {
			    'issue_number': re.search(issue_number_pattern, text),
			    'order_number': re.search(order_number_pattern, text),
			    'day': re.search(day_pattern, text, re.IGNORECASE),
			    'month': re.search(month_pattern, text),
			    'year': re.search(year_pattern, text)
			}

			for key, value in result_dict.items():
			    if value is None:
			        result_dict[key] = None
			    else:
			        result_dict[key] = value.group(0)
			        if key == "month":
			        	result_dict[key] = value.group(1)

			issue_number = result_dict['issue_number']
			order_number = result_dict['order_number']
			day = result_dict['day']
			month = result_dict['month']
			year = result_dict['year']

			saved_issue_number_match = saved_issue_number_match if saved_issue_number_match else issue_number
			saved_order_number_match = saved_order_number_match if saved_order_number_match else order_number
			saved_day_match = saved_day_match if saved_day_match else day
			saved_month_match = saved_month_match if saved_month_match else month
			saved_year_match = saved_year_match if saved_year_match else year

			if attempt > 0:
				print(f"\nСохраненные распознанные элементы: \n{saved_issue_number_match} {saved_order_number_match} {saved_day_match} {saved_month_match} {saved_year_match}")
				issue_number = saved_issue_number_match if saved_issue_number_match else issue_number
				order_number = saved_order_number_match if saved_order_number_match else order_number
				day = saved_day_match if saved_day_match else day
				month = saved_month_match if saved_month_match else month
				year = saved_year_match if saved_year_match else year		

			if attempt == total_attempts:
				day = "___" if not day else day

			print(f"\nРаспознанные элементы со страницы: \n{issue_number}, {order_number}, {day}, {month}, {year}")
		
			if issue_number and order_number and day and month and year:

				print("\nНачало нового выпуска\n")
				issue_number = int(issue_number.replace("№", ""))
				order_number = re.sub(r"[()\s]+", "", order_number)
				day = day.replace(' ', '').replace("\n", '')
				month = month_dict[month.lower()]
				day_month = day+ "_" + month if len(day) > 1 else str(0) + day + "_" + month
				year = year.replace(" ","")

				# Если уже был обработан какой-то выпуск газеты, сохраняем его в pdf-файл
				if current_issue_number is not None:
					print("Сохранение текущего выпуска, перед началом нового")
					
					current_issue_pages[0].save(images_folder+"pdfs\\"+output_filename, "PDF" ,resolution=100.0, save_all=True, append_images=current_issue_pages[1:])

					if n > 4:
						print("\nСкорее всего что-то не так")
						current_issue_pages[0].save(questionable_folder+output_filename, "PDF" ,resolution=100.0, save_all=True, append_images=current_issue_pages[1:])
					n=0
					current_issue_pages = []
					
				current_issue_pages.append(Image.open(image_path))
				# Обновление информации о текущем выпуске газеты
				current_issue_number = issue_number
				current_issue_order_number = order_number
				current_issue_day_month = day_month
				current_issue_year = year
				output_filename = f"[{current_issue_order_number}]_Восход.-{current_issue_year}.-{current_issue_day_month}(№{current_issue_number}).pdf"
				n += 1
				recognized = True
				print(f"Страниц: {n}\n")

			else:
				probably_recognizable = True
		else:
			print("Нет совпадений")
			return recognized, probably_recognizable, Matches, image_path

		return recognized, probably_recognizable, Matches, image_path
	else:
		return True, False, False, False

# Обход всех файлов в папке с изображениями в порядке сортировки
for image_filename in sorted(os.listdir(images_folder)):
	
	recognized, probably_recognizable, Matches, image_path = recog(image_filename)

	if probably_recognizable:
		print("Проблема со считыванием текста")
		while attempt < total_attempts:
			rescaling += rescaling_coef
			attempt += 1
			print(f"\nНовая попытка: {attempt}")
			recognized, probably_recognizable, Matches, image_path = recog(image_filename)
			if recognized:
				print(f"\n\nПопытка {attempt} прошла успешно")
				break
			if not Matches:
				print(f"\n\nПри попытке {attempt} не нашлось совпадений")
				break

		if not recognized:
			pic = Image.open(image_path) 
			filename = os.path.basename(image_path)
			pic.save(os.path.join(unreadable, filename))
			print("\nНе удалось получить нужный текст со страницы")    

	attempt = 0
	saved_issue_number_match = None
	saved_order_number_match = None
	saved_day_match = None
	saved_month_match = None
	saved_year_match = None

	if not recognized:    
		n += 1
		print(f"Страниц: {n}\n")
		current_issue_pages.append(Image.open(image_path))
		print()
			

	if i == len(os.listdir(images_folder))-2:
		print("\nПоследний выпуск\n")
		print(f"Страниц: {n}\n")
		current_issue_pages[0].save(images_folder+"pdfs\\"+output_filename, "PDF" ,resolution=100.0, save_all=True, append_images=current_issue_pages[1:])
	i += 1