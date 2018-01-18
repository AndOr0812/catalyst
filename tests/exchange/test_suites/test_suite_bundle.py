import random

import os
import pandas as pd
from logbook import TestHandler
from pandas.util.testing import assert_frame_equal

from catalyst import get_calendar
from catalyst.exchange.exchange_asset_finder import ExchangeAssetFinder
from catalyst.exchange.exchange_data_portal import DataPortalExchangeBacktest
from catalyst.exchange.utils.exchange_utils import get_candles_df
from catalyst.exchange.utils.factory import get_exchange
from catalyst.exchange.utils.test_utils import output_df, \
    select_random_assets

pd.set_option('display.expand_frame_repr', False)
pd.set_option('precision', 8)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', 1000)


class TestSuiteBundle:
    @staticmethod
    def get_data_portal(exchanges):
        open_calendar = get_calendar('OPEN')
        asset_finder = ExchangeAssetFinder(exchanges)

        exchange_names = [exchange.name for exchange in exchanges]
        data_portal = DataPortalExchangeBacktest(
            exchange_names=exchange_names,
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=None  # will set dynamically based on assets
        )
        return data_portal

    def compare_bundle_with_exchange(self, exchange, assets, end_dt, bar_count,
                                     freq, data_frequency, data_portal):
        """
        Creates DataFrames from the bundle and exchange for the specified
        data set.

        Parameters
        ----------
        exchange: Exchange
        assets
        end_dt
        bar_count
        freq
        data_frequency
        data_portal

        Returns
        -------

        """
        data = dict()

        log_catcher = TestHandler()
        with log_catcher:
            data['bundle'] = data_portal.get_history_window(
                assets=assets,
                end_dt=end_dt,
                bar_count=bar_count,
                frequency=freq,
                field='close',
                data_frequency=data_frequency,
            )
            candles = exchange.get_candles(
                end_dt=end_dt,
                freq=freq,
                assets=assets,
                bar_count=bar_count,
            )
            data['exchange'] = get_candles_df(
                candles=candles,
                field='close',
                freq=freq,
                bar_count=bar_count,
                end_dt=end_dt,
            )
            for source in data:
                df = data[source]
                path, folder = output_df(
                    df, assets, '{}_{}'.format(freq, source)
                )

            assert_frame_equal(
                right=data['bundle'],
                left=data['exchange'],
                check_less_precise=1,
            )
            try:
                assert_frame_equal(
                    right=data['bundle'],
                    left=data['exchange'],
                    check_less_precise=min([a.decimals for a in assets]),
                )
            except Exception as e:
                print('Some differences were found within a 1 decimal point '
                      'interval of confidence: {}'.format(e))
                with open(os.path.join(folder, 'compare.txt'), 'w+') as handle:
                    handle.write(e.args[0])

            print('saved test results: {}'.format(folder))
            pass

    def test_validate_bundles(self):
        # exchange_population = 3
        asset_population = 3
        data_frequency = random.choice(['minute'])

        # bundle = 'dailyBundle' if data_frequency
        #  == 'daily' else 'minuteBundle'
        # exchanges = select_random_exchanges(
        #     population=exchange_population,
        #     features=[bundle],
        # )  # Type: list[Exchange]
        exchanges = [get_exchange('poloniex', skip_init=True)]

        data_portal = TestSuiteBundle.get_data_portal(exchanges)
        for exchange in exchanges:
            exchange.init()

            frequencies = exchange.get_candle_frequencies(data_frequency)
            freq = random.sample(frequencies, 1)[0]

            bar_count = random.randint(1, 10)

            assets = select_random_assets(
                exchange.assets, asset_population
            )
            end_dt = None
            for asset in assets:
                attribute = 'end_{}'.format(data_frequency)
                asset_end_dt = getattr(asset, attribute)

                if end_dt is None or asset_end_dt < end_dt:
                    end_dt = asset_end_dt

            dt_range = pd.date_range(
                end=end_dt, periods=bar_count, freq=freq
            )
            self.compare_bundle_with_exchange(
                exchange=exchange,
                assets=assets,
                end_dt=dt_range[-1],
                bar_count=bar_count,
                freq=freq,
                data_frequency=data_frequency,
                data_portal=data_portal,
            )
        pass
