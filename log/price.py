import numpy as np
from log.constant import *
import log.logdb as logdb;
import tensorflow as tf

TIME_WIDTH = 128
BOARD_WIDTH = 32
BOARD_TIME_WIDTH = TIME_WIDTH + 1
NUMBER_OF_LAYERS = 4

class PriceBoard:
    """
    represent order book board and its history

    Layer 1   Buy order     (0 edge)
    Layer 2   Sell Order    (other side)
    Layer 3   Buy Trade & funding minus (0 edge)
    Layer 4   Sell Trade & funding plus (other side)

    """
    def __init__(self):
        self.current_time = 0
        self.center_price = 0

        self.sell_trade = np.zeros((BOARD_TIME_WIDTH, BOARD_WIDTH))
        self.buy_trade = np.zeros((BOARD_TIME_WIDTH, BOARD_WIDTH))
        self.sell_order = np.zeros((BOARD_TIME_WIDTH, BOARD_WIDTH))
        self.buy_order = np.zeros((BOARD_TIME_WIDTH, BOARD_WIDTH))

        self.my_sell_order = {}
        self.my_buy_order = {}

        self.market_sell_price = 0
        self.market_buy_price = 0

        self.fix_sell_price = 0
        self.fix_buy_price = 0

        self.funding_ttl = 0
        self.funding = 0

        self.best_action = ACTION.NOP


    def add_sell_order(self, price, size):
        if price in self.my_sell_order:
            self.my_sell_order[price] += size
        else:
            self.my_sell_order[price] = size

    def add_buy_order(self, price, size):
        if price in self.buy_order:
            self.my_buy_order[price] += size
        else:
            self.my_buy_order[price] = size

    def set_origin_time(self,time):
        self.current_time = time

    def get_origin_time(self):
        return self.current_time

    def set_center_price(self, price):
        self.center_price = price

    def get_center_price(self):
        return self.center_price

    def get_position(self, time, price):
        t = int(self.current_time - time) + 1 # first line[0] is for actual
        p = int((price - self.center_price) / PRICE_UNIT + BOARD_WIDTH / 2)

        if p < 0 or BOARD_WIDTH <= p:
            return None

        return t, p

    def set_sell_order_book(self, time, price, line):
        width = 0

        data_width = 0
        for vol in line:
            pos = self.get_position(time, price)
            if not pos:
                break

            t, p = pos
            self.sell_order[t, p] = vol
            price += PRICE_UNIT
            width += 1

            data_width = data_width + 1

            if ORDER_BOOK_DATA_LIMIT < width:
                break

        if(data_width < 10):
            print('data width->', data_width, line)


    def set_buy_order_book(self, time, price, line):
        width = 0

        valid_line = False

        for vol in line:
            pos = self.get_position(time, price)

            if not pos:
                # print("error in BUY pos", time, price)
                break

            t, p = pos
            self.buy_order[t, p] = vol

            if vol:
                valid_line = True

            price -= PRICE_UNIT
            width += 1
            if ORDER_BOOK_DATA_LIMIT < width:
                break

        if valid_line is False:
            print('INVALIDLINE---->', time, price, line)

    def add_buy_trade(self, time, price, volume, window=1):
        pos = self.get_position(time, price)
        if pos:
            t, p = pos
            self.buy_trade[t][p] = self.buy_trade[t][p] + volume / window

    def add_sell_trade(self, time, price, volume, window=1):
        pos = self.get_position(time, price)
        if pos:
            t, p = pos
            self.sell_trade[t][p] = self.sell_trade[t][p] + volume / window

    def set_funding(self, ttl, funding):
        print("fundig->", ttl, funding)
        self.funding = funding
        self.funding_ttl = ttl

    def save(self, filename):
        #todo: not implemented
        print("---dummy---")
        np.save(filename + "sell_order", self.sell_order)
        np.save(filename + "buy_order", self.buy_order)
        np.save(filename + "buy_trade", self.buy_trade)
        np.save(filename + "sell_trade", self.sell_trade)

        np.savez_compressed(filename + "sell_order", self.sell_order)
        np.savez_compressed(filename + "buy_order", self.buy_order)
        np.savez_compressed(filename + "buy_trade", self.buy_trade)
        np.savez_compressed(filename + "sell_trade", self.sell_trade)

        #np.savez_compressed(filename, self.data)

    def feature_int64(self, a):
        return tf.train.Feature(int64_list=tf.train.Int64List(value=[a]))

    def feature_bytes(self, a):
        return tf.train.Feature(bytes_list=tf.train.BytesList(value=[a]))

    def save_tf_record(self, output_file='/tmp/data.tfrecords'):
        pio = tf.python_io

        writer = pio.TFRecordWriter(str(output_file), options=pio.TFRecordOptions(pio.TFRecordCompressionType.GZIP))
#        writer = pio.TFRecordWriter(str(output_file))

        record = self._tf_example_record()

        writer.write(record.SerializeToString())

        writer.close()

    def _tf_example_record(self):
        record = tf.train.Example(features=tf.train.Features(feature={
            'buy': self.feature_bytes(self.buy_order.tobytes()),
            'sell': self.feature_bytes(self.sell_order.tobytes()),
            'buy_trade': self.feature_bytes(self.buy_trade.tobytes()),
            'sell_trade': self.feature_bytes(self.sell_trade.tobytes()),
            'market_buy_price': self.feature_int64(self.market_buy_price),
            'market_sell_price': self.feature_int64(self.market_sell_price),
            'fix_buy_price': self.feature_int64(self.fix_buy_price),
            'fix_sell_price': self.feature_int64(self.fix_sell_price),
            'ba': self.feature_int64(self.best_action),
            'time': self.feature_int64(self.current_time)
            }))

        return record


    def load_tf_record(self, input_file_name='/tmp/data.tfrecords'):
        with tf.Session() as sess:
            dataset = tf.data.TFRecordDataset(input_file_name, compression_type='GZIP')
            dataset2 = dataset.map(PriceBoard.read_tfrecord)
            iterator = dataset2.make_initializable_iterator()
            next_dataset = iterator.get_next()
            sess.run(iterator.initializer)
            buy, sell, buy_trade, sell_trade, market_buy_price, \
                   market_sell_price, fix_buy_price, fix_sell_price, ba, time = sess.run(next_dataset)

        self.buy = np.frombuffer(buy, dtype=np.uint8).reshape(BOARD_TIME_WIDTH, BOARD_WIDTH)
        self.sell= np.frombuffer(sell, dtype=np.uint8).reshape(BOARD_TIME_WIDTH, BOARD_WIDTH)
        self.buy_trade = np.frombuffer(buy_trade, dtype=np.uint8).reshape(BOARD_TIME_WIDTH, BOARD_WIDTH)
        self.sell_trade = np.frombuffer(sell_trade, dtype=np.uint8).reshape(BOARD_TIME_WIDTH, BOARD_WIDTH)
        self.market_buy_price = market_buy_price
        self.market_sell_price = market_sell_price
        self.fix_buy_price = fix_buy_price
        self.fix_sell_price = fix_sell_price
        self.ba = ba
        self.time = time


    @staticmethod
    def read_tfrecord(serialized):
        buy = None
        time = None

        features = tf.parse_single_example(
            serialized,
            features={
                'buy': tf.FixedLenFeature([], tf.string),
                'sell': tf.FixedLenFeature([], tf.string),
                'buy_trade': tf.FixedLenFeature([], tf.string),
                'sell_trade': tf.FixedLenFeature([], tf.string),
                'market_buy_price': tf.FixedLenFeature([], tf.int64),
                'market_sell_price': tf.FixedLenFeature([], tf.int64),
                'fix_buy_price': tf.FixedLenFeature([], tf.int64),
                'fix_sell_price': tf.FixedLenFeature([], tf.int64),
                'ba': tf.FixedLenFeature([], tf.int64),
                'time': tf.FixedLenFeature([], tf.int64)
            })

        buy = features['buy']
        sell= features['sell']
        buy_trade = features['buy_trade']
        sell_trade = features['sell_trade']
        market_buy_price = features['market_buy_price']
        market_sell_price = features['market_sell_price']
        fix_buy_price = features['fix_buy_price']
        fix_sell_price = features['fix_sell_price']
        ba = features['ba']
        time = features['time']

        return  buy,    sell,     buy_trade,    sell_trade,    market_buy_price,\
                market_sell_price,    fix_buy_price,    fix_sell_price, ba,  time

    def load(self, filename):
        pass

    def calc_static(self, a):
        """
        calc matrix non zero mean and stddev
        :param a: matrix to be examine
        :return: mean, stddev
        """
        item_no = np.nonzero(a)[0].size
        non_zero_sum = np.sum(a)
        non_zero_sq_sum = np.sum(np.square(a))

        variant = non_zero_sq_sum / item_no - (non_zero_sum / item_no)**2

        return non_zero_sum/item_no, variant ** 0.5

    def normalize(self):
        order_mean, order_stddev = self.calc_static(self.sell_order + self.buy_order)
        trade_mean, trade_stddev = self.calc_static(self.sell_trade + self.buy_trade)

        self.buy_order = self.normalize_array(self.buy_order, order_mean + order_stddev / 2)
        self.sell_order = self.normalize_array(self.sell_order, order_mean + order_stddev / 2)

        self.buy_trade = self.normalize_array(self.buy_trade, trade_mean + trade_stddev)
        self.sell_trade = self.normalize_array(self.sell_trade, trade_mean + trade_stddev)

    def normalize_array(self, array, max_value):
        float_array = array * (256 / max_value)
        uint8_array = np.ceil(np.clip(float_array, 0, 255)).astype('uint8')

        return uint8_array


class PriceBoardDB(PriceBoard):
    @staticmethod
    def load_from_db(time, db_name = "/tmp/bitlog.db"):
        db = logdb.LogDb(db_name)
        db.connect()
        db.create_cursor()

        board = PriceBoardDB()

        board.set_origin_time(time)

        center_price = db.select_center_price(time)
        if not center_price:
            print('---DBEND---')
            return None

        board.set_center_price(center_price)

        print(time)

        error_count = 0
        query_time = time
        time_window = 1

        for offset in range(0, TIME_WIDTH):
            if not PriceBoardDB.load_from_db_time(db, board, time, offset, query_time, time_window):
                error_count = error_count + 1
            query_time = query_time - time_window

            if time - query_time < 8:
                pass
            elif time - query_time < 16:
                time_window = 2
            elif time - query_time < 32:
                time_window = 3
            elif time - query_time < 64:
                time_window = 4
            elif time - query_time < 128:
                time_window = 5
            else:
                time_window = 6

        board.normalize()

        #load prices
        prices = db.select_order_book_price()
        board.market_sell_price = 0
        board.market_buy_price = 0

        board.fix_sell_price = 0
        board.fix_buy_price = 0

        #load funding
        funding = db.select_funding(time)

        if funding:
            t, p = funding
            board.funding_ttl = 0
            board.funding = 0

        if 10 < error_count:
            return None

        return board


    @staticmethod
    def load_from_db_time(db, board, time_origin, offset, query_time, time_window=1):

        #load sell order
        for t, price, volume in db.select_sell_trade(query_time, time_window):
            board.add_sell_trade(time_origin - offset, price, volume / time_window)

        #load buy order
        for t, price, volume in db.select_buy_trade(query_time, time_window):
            board.add_buy_trade(time_origin - offset, price, volume / time_window)

        #load order book
        order_book = None

        max_retry = 100
        if time_window < max_retry:
            max_retry = time_window + 50

        retry = 0
        while(not order_book and retry < max_retry):
            order_book = db.select_order_book(query_time - retry)
            retry = retry + 1
            if not order_book:
                print("retry order book", query_time - retry, time_origin - query_time)

        if order_book:
            t, sell_min, sell_book, buy_max, buy_book = order_book
            board.set_sell_order_book(time_origin - offset, sell_min, sell_book)
            if(len(sell_book) < 10):
                print("shot->", time_origin - offset, sell_book)

            board.set_buy_order_book(time_origin - offset, buy_max, buy_book)

            return True
        else:
            print("NO ORDERBOOK FOUND->", query_time)
            return False
