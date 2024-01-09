from mycroft import MycroftSkill, intent_file_handler, intent_handler
from adapt.intent import IntentBuilder
from mycroft.skills.context import removes_context
from mycroft.util import LOG
import time
import cv2
import os
import sys
from multiprocessing import Process, Queue
import csv
import json

from .cvAPI import getDetail, getObjLabel

LOGSTR = '********************====================########## '

MODE = 'TEST'

TEST_IMAGE_PATH_MULTI = '/home/yatharth/Documents/ISY5005/SRBP/SRBP_Day_2_References/testPhoto/multi.jpeg'

TEST_IMAGE_PATH_HAND = '/home/yatharth/Documents/ISY5005/SRBP/SRBP_Day_2_References/testPhoto/3.jpeg'

IMAGE_STORE_PATH = '/home/yatharth/Pictures/Webcam'

def take_photo(img_queue):
    '''
    Do taking photo
    '''
    LOG.info(LOGSTR + 'take photo process start')
    cap = cv2.VideoCapture(0)
    img_name = 'cap_img_' + str(time.time()) + '.jpg'
    img_path = IMAGE_STORE_PATH + img_name # Remember to update path to image

    #<-- Take photo in specific time duration -->
    cout = 0
    while True:
        ret, frame = cap.read()
        cv2.waitKey(1)
        cv2.imshow('capture', frame)
        cout += 1 
        if cout == 50:
            img_queue.put(img_path)
            cv2.imwrite(img_path, frame)
            break

    cap.release()
    cv2.destroyAllWindows()
    LOG.info(LOGSTR + 'take photo process end')
    os._exit(0)


def generate_str(possible_list):
    '''
    Generate string for Mycroft to speak it

    Args: 
        possible_list: array list with len = 3, each element is a string
    Returns:
        a string, e.g. possible_list = ['a', 'b', 'c'], res = 'a, b, and c'
    '''
    res = ''
    if len(possible_list) == 3:
        res = possible_list[0] + ' ' + \
            possible_list[1] + ' and ' + possible_list[2]
    elif len(possible_list) == 2:
        res = possible_list[0] + ' and ' + possible_list[1]
    elif len(possible_list) == 1:
        res = possible_list[0]

    return res



class EasyShopping(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.img_multi = ''
        self.category_str = ''
        self.color_str = ''
        self.brand_str = ''
        self.kw_str = ''
    
    def initialize(self):
        self.reload_skill = False

    def clear_all(self):
        self.types_str = ''
        self.color_str = ''
        self.logo_str = ''
        self.kw_str = ''
        self.img_hand = ''
        self.img_multi = ''

    @intent_file_handler('shopping.easy.intent')
    def handle_shopping_easy(self, message):
        self.speak_dialog('shopping.easy')
    
    def handle_no_context1(self, message):
        self.speak('Please let me have a look what is in front of you')
        
        take_photo = self.ask_yesno('do.you.want.to.take.a.photo')
        if take_photo == 'yes':
            self.handle_view_goods(message)
        elif take_photo == 'no':
            self.speak('OK, I will not take a photo.')
        else:
            self.speak('I cannot understand your answer. Please say yes or no.')
    
    def handle_ask_item_detail(self, detail, detail_str):
        if detail_str == '':
            self.speak_dialog(
            'cannot.get', {'detail': detail}, expect_response=True)
        else:
            dialog_str = 'item.' + detail
            self.speak_dialog(dialog_str, {detail: detail_str}, expect_response=True)
    
    @intent_handler(IntentBuilder('ViewItemInHand').require('ViewItemInHandKeyWord'))
    def handle_view_item_in_hand(self, message):
        self.speak_dialog('take.photo')
        self.img_multi = ''
        self.img_hand = ''
        
        img_queue = Queue()
        take_photo_process = Process(target=take_photo, args=(img_queue,))
        take_photo_process.daemon = True
        take_photo_process.start()
        take_photo_process.join()
        self.img_hand = img_queue.get()

        try:
            self.log.info(LOGSTR + 'actual img path')
            self.log.info(self.img_hand)
            if MODE == 'TEST':
                self.log.info(LOGSTR + 'testing mode, use another image')
                self.img_hand = TEST_IMAGE_PATH_HAND

            detail = getDetail(self.img_hand)
            self.detail = detail

            self.category_str = generate_str(detail['objectLabel'])

            if self.category_str != '':
                self.set_context('getDetailContext')
                self.speak_dialog(
                    'item.category', {'category': self.category_str}, expect_response=True)

                self.brand_str = generate_str(detail['objectLogo'])

                color_list = []
                for color in detail['objectColor']:
                    color_list.append(color['colorName'])
                self.color_str = generate_str(color_list)

                self.kw_str = ' '.join(detail['objectText'])

            else:
                self.clear_all()
                self.remove_context('getDetailContext')
                self.speak(
                    'I cannot understand what is in your hand. Maybe turn around it and let me see it again', expect_response=True)
                

        except Exception as e:
            self.log.error((LOGSTR + "Error: {0}").format(e))
            self.speak_dialog(
                "exception", {"action": "calling computer vision API"})


    @intent_handler(IntentBuilder('AskItemCategory').require('Category').require('getDetailContext').build())
    def handle_ask_item_category(self, message):
        self.handle_ask_item_detail('category', self.category_str)

    @intent_handler(IntentBuilder('AskItemColor').require('Color').require('getDetailContext').build())
    def handle_ask_item_color(self, message):
        self.handle_ask_item_detail('color', self.color_str)

    @intent_handler(IntentBuilder('AskItemBrand').require('Brand').require('getDetailContext').build())
    def handle_ask_item_brand(self, message):
        self.handle_ask_item_detail('brand', self.brand_str)

    @intent_handler(IntentBuilder('AskItemKw').require('Kw').require('getDetailContext').build())
    def handle_ask_item_keywords(self, message):
        self.handle_ask_item_detail('keyword', self.kw_str)

    @intent_handler(IntentBuilder('AskItemInfo').require('Info').require('getDetailContext').build())
    def handle_ask_item_complete_info(self, message):
        self.speak_dialog('item.complete.info', {'category': self.category_str})
        self.handle_ask_item_detail('color', self.color_str)
        self.handle_ask_item_detail('brand', self.brand_str)
        self.handle_ask_item_detail('keyword', self.kw_str)

    
    # @intent_handler(IntentBuilder('FinishOneItem').require('Finish').require('getDetailContext').build())
    # @removes_context('getDetailContext')
    # def handle_finish_current_item(self, message):
    #     self.speak('Got you request. Let\'s continue shopping!')
    #     self.types_str = ''
    #     self.color_str = ''
    #     self.logo_str = ''
    #     self.kw_str = ''
    #     self.img_hand = ''
    #     self.img_multi = ''
    

    @intent_handler('not.take.item.intent')
    @removes_context('getDetailContext')
    def handle_finish_current_item_not_take(self, message):
        if self.img_hand != '':
            self.speak('Don\'t put it into cart. Let\'s continue shopping!')
            self.clear_all()
        else:
            self.speak('Sorry, I don\'t understand')


    @intent_handler('take.item.intent')
    @removes_context('getDetailContext')
    def handle_finish_current_item_take(self, message):
        if self.img_hand != '':
            self.speak('I will put the item into cart. Let\'s continue shopping!')
            self.clear_all()
        else:
            self.speak('Sorry, I don\'t understand')

    @intent_handler(IntentBuilder('NoContext').one_of('Category', 'Color', 'Brand', 'Kw', 'Info'))
    def handle_no_context2(self, message):
        self.speak('Please let me have a look at what\'s on your hand first.')
        take_photo = self.ask_yesno('do.you.want.to.take.a.photo')
        if take_photo == 'yes':
            self.handle_view_item_in_hand(message)
        elif take_photo == 'no':
            self.speak('OK. I won\'t take photo')
        else:
            self.speak('I cannot understand what you are saying')


    @intent_handler('is.there.any.goods.intent')
    def handle_is_there_any_goods(self, message):
        if self.img_multi == '':
            self.handle_no_context1(message)

        else:
            # call cv api, and get result. 
            try:
                self.log.info(LOGSTR + 'actual img path')
                self.log.info(self.img_multi)
                if MODE == 'TEST':
                    self.log.info(LOGSTR + 'testing mode, use another image')
                    self.img_multi = TEST_IMAGE_PATH_MULTI

                objectlist = getObjLabel.getObjectsThenLabel(self.img_multi)
                label_list = []
                loc_list = []
                detected = 0

                category_label = message.data.get('category')

                for obj in objectlist['objectList']:
                    label_list.append(obj['name'])
                    loc_list.append(obj['loc'])
            
                if category_label:
                    for i in range(0,len(label_list)):
                        label_str = generate_str(label_list[i])
                        label_str = label_str.lower()
                
                        if category_label is not None:
                            if category_label in label_str:
                                self.speak_dialog('yes.goods',
                                            {'category': category_label,
                                            'location': loc_list[i]})
                                detected = 1
                                break
                        else:
                            continue

                if detected == 0 and category_label:
                    self.speak_dialog('no.goods',
                    {'category': category_label})

            except Exception as e:
                self.log.error((LOGSTR + "Error: {0}").format(e))
                self.speak_dialog(
                "exception", {"action": "calling computer vision API"})


    @intent_handler('view.goods.intent')
    def handle_view_goods(self, message):
        self.speak_dialog('take.photo')

        self.img_multi = ''
        self.img_hand = ''

        img_queue = Queue()
        take_photo_process = Process(target=take_photo, args=(img_queue,))
        take_photo_process.daemon = True
        take_photo_process.start()
        take_photo_process.join()
        self.img_multi = img_queue.get()

        self.speak('I find some goods here, you can ask me whatever goods you want.', expect_response=True)

    


def create_skill():
    return EasyShopping()
