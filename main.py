from selenium import webdriver
from selenium.webdriver.common.by import By

from fake_useragent import UserAgent

from loguru import logger

import time
import datetime
import os
import sys


URL = 'https://www.kinopoisk.ru/lists/movies/top_1000/'

COLUMNS = ['Название фильма', 'Рейтинг', 'Страна', 'Год', 'Режиссёр', 'Наличие на Кинопоиск']


class Parser:
    def __init__(self, url: str):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        ua = UserAgent(platforms='desktop')
        uar = ua.random        
        options.add_argument(f'user-agent={uar}')
                
        self.driver = webdriver.Chrome(options=options)
        
        time.sleep(2)
        
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": uar})
        
        time.sleep(2)
        
        logger.success('Скрипт успешно запущен')
            
    @staticmethod
    def check_temp() -> int | None:
        '''Возвращает номер страницы, на котором остановился предыдущий парсинг, либо None'''
        
        # Проверка наличия файла temp
        if not os.path.exists('temp'):
            # Если не найден, то будет создан
            open('temp', 'w', encoding='utf-8').close()
            return None
        
        with open('temp', 'r', encoding='utf-8') as tfile:
            lines = tfile.readlines()
            
        # Чистка списка строк от пустых строк в конце
        while lines and lines[-1].isspace():
            lines.pop()
            
        return len(lines)//50 + 1
    
    def get_top(self):
        '''Получает топ 1000 фильмов с сайта Кинопоиск'''
        
        if Parser.check_temp():
            logger.warning('Обнаружен незавершенный предыдущий сбор данных')
            page = Parser.check_temp()
        else:
            page = 1
        
        while page <= 20:
            # Переход на нужную страницу
            self.flip_page(page)
            
            # Сбор данных с текущей страницы
            new_data = []
            for i in range(3, 53):
                new_data.append(self.get_movie_info(i))
            
            # Запись данных с текущей страницы
            self.write_temp(new_data)
            logger.info(f'Информация со страницы {page} собрана')
                        
            page += 1
        
        self.write_result()
    
    def get_movie_info(self, i: int) -> tuple | None:
        '''Получает название фильма, рейтинг, год выхода, страну производства, режиссера, возможность просмотра на кинопоиске'''
        
        elem = self.driver.find_element(By.XPATH, f'//*[@id="__next"]/div[1]/div[2]/div[2]/div[3]/main/div[{i}]')        
        spans = [span.text for span in elem.find_elements(By.CSS_SELECTOR, 'span') if span.text != '']              # Вся текст. инф-я хранится в <span>
        kp = elem.find_elements(By.XPATH, './/div[contains(text(), "По подписке") and contains(text(), "Плюс")]')
        
        # Если никакой текстовой информации не было найдено
        if not spans:
            return None
        
        name = spans[0]
        if len(spans) in [6, 7]:
            rate = spans[-2]
            year = spans[-5].split(', ')[1 if len(spans) == 7 else 0]
            country = spans[-4].split(' • ')[0]
            director = spans[-4].split(': ')[-1]
        else:
            rate = '-'
            year = spans[2].split(', ')[1]
            country = spans[3].split(' • ')[0]
            director = spans[3].split(': ')[-1]
            
        return (
            name, rate, year, country, director, 'True' if kp else 'False'
        )
    
    def flip_page(self, page: int):
        '''Переходит на требуемую страницу'''
        
        self.driver.get(URL + f'?page={page}')
        self.wait_ready()
        logger.info(f'Выполнен переход на страницу {page}')
        time.sleep(1)

    def wait_ready(self):
        '''Ожидает полной загрузки страницы'''
        
        while True:
            state = self.driver.execute_script("return document.readyState")
            if state == "complete":
                break
            time.sleep(0.5)
    
        if URL not in self.driver.current_url:
            logger.critical('Загружена не та страница! Возможно капча. Требуется вмешательство человека. Нажать enter по завершении')
            input()
    
    def write_temp(self, new_data: list[tuple]):
        '''Записывает собранную со страницы информацию в промежуточное хранилище'''
        
        with open('temp', 'a', encoding='utf-8') as tfile:
            for line in new_data:
                if line:
                    tfile.write(';'.join(line))
                    tfile.write('\n')
    
    def write_result(self):
        '''Записывает результат в выходной файл'''
        
        with open('temp', 'r', encoding='utf-8') as tfile:
            tdata = tfile.read()

        result_file = f'result_{datetime.datetime.now().date()}.csv'
        with open(result_file, 'w', encoding='utf-8') as rfile:
            rfile.write(';'.join(COLUMNS))
            rfile.write('\n')
            rfile.write(tdata)
            
        os.remove('temp')
            
        logger.success(f'Результат сбора записан в файл: \033[4m{result_file}')


def logger_prepare():
    '''Настройка форматирования логгера'''
    logger.remove(0)
    logger.add(sys.stderr, format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>')
    

if __name__ == "__main__":
    logger_prepare()
    
    parser = Parser(URL)
    time.sleep(2)
    parser.get_top()
    