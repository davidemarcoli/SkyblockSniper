import asyncio
import re
import os
import webbrowser

op = os.name == 'nt'
if op: import winsound
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
import time

import pandas as pd
import requests
from colorama import Fore, Style

from plyer import notification

c = requests.get("https://api.hypixel.net/skyblock/auctions?page=0")
resp = c.json()
now = resp['lastUpdated']
toppage = resp['totalPages']

results = []
searchableResults = []
prices = {}

# stuff to remove
REFORGES = [" ✦", "⚚ ", " ✪", "✪", "Stiff ", "Lucky ", "Jerry's ", "Dirty ", "Fabled ", "Suspicious ", "Gilded ",
            "Warped ", "Withered ", "Bulky ", "Stellar ", "Heated ", "Ambered ", "Fruitful ", "Magnetic ", "Fleet ",
            "Mithraic ", "Auspicious ", "Refined ", "Headstrong ", "Precise ", "Spiritual ", "Moil ", "Blessed ",
            "Toil ", "Bountiful ", "Candied ", "Submerged ", "Reinforced ", "Cubic ", "Warped ", "Undead ",
            "Ridiculous ", "Necrotic ", "Spiked ", "Jaded ", "Loving ", "Perfect ", "Renowned ", "Giant ", "Empowered ",
            "Ancient ", "Sweet ", "Silky ", "Bloody ", "Shaded ", "Gentle ", "Odd ", "Fast ", "Fair ", "Epic ",
            "Sharp ", "Heroic ", "Spicy ", "Legendary ", "Deadly ", "Fine ", "Grand ", "Hasty ", "Neat ", "Rapid ",
            "Unreal ", "Awkward ", "Rich ", "Clean ", "Fierce ", "Heavy ", "Light ", "Mythic ", "Pure ", "Smart ",
            "Titanic ", "Wise ", "Bizarre ", "Itchy ", "Ominous ", "Pleasant ", "Pretty ", "Shiny ", "Simple ",
            "Strange ", "Vivid ", "Godly ", "Demonic ", "Forceful ", "Hurtful ", "Keen ", "Strong ", "Superior ",
            "Unpleasant ", "Zealous "]

# Constant for the lowest priced item you want to be shown to you; feel free to change this
LOWEST_PRICE = 20000
HIGHEST_PRICE = 2000000

# Constant to turn on/off desktop notifications
NOTIFY = True

# Constant for the lowest percent difference you want to be shown to you; feel free to change this
LOWEST_PERCENT_MARGIN = 2 / 3

START_TIME = default_timer()

from pynput import keyboard
import threading


# r = requests.get("https://sky.coflnet.com/api/item/price/ASPECT_OF_THE_DRAGON/history/day")
# result = r.json()
# print(result)
# print(result[-1])
# print(result[-1]['min'])


# def copy_result(i):
#     print('Function 1 activated')
#
# with keyboard.GlobalHotKeys({
#     '<alt>+<ctrl>+r': copy_result(1),
#     '<alt>+<ctrl>+t': function_1,
#     '<alt>+<ctrl>+y': function_2}) as h:
#     h.join()

def on_press(key):
    # if hasattr(key, 'vk'):
    #     print(key.vk)
    if hasattr(key, 'vk') and 96 <= key.vk <= 105:
        print('You entered a number from the numpad: ', key.vk - 96)
        try:
            print(searchableResults[key.vk - 96])
            print("Copying Auction " + searchableResults[key.vk - 96][0])
            df = pd.DataFrame(['/viewauction ' + searchableResults[key.vk - 96][0]])
            df.to_clipboard(index=False, header=False)
            item_name = searchableResults[key.vk - 96][1]
            for reforge in REFORGES: item_name = item_name.replace(reforge, "")
            r = requests.get(
                "https://sky.coflnet.com/api/item/price/" + '_'.join(item_name.upper().split()) + "/history/week")
            if r.status_code == 200:
                result = r.json()
                # print(result)
                print("Current Min: " + Fore.BLUE + result[-1]['min'] + Style.RESET_ALL)
                print("Average Min: " + Fore.MAGENTA + str(get_average_property(result, 'min')) + Style.RESET_ALL)
                webbrowser.open("https://sky.coflnet.com/item/" + '_'.join(item_name.upper().split()) + "?range=week",
                                autoraise=False)
            else:
                print("Item Not Found")

        except IndexError:
            print("Auction not found!")


def get_average_property(objects, property_name):
    print("len")
    print(len(objects))
    total = 0
    count = 0
    for obj in objects:
        print(obj)
        print(obj[property_name])
        if obj[property_name]:
            total += obj[property_name]
            count += 1
    if count == 0:
        return 0
    else:
        return total / count


def listen_to_keypresses():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


def fetch(session, page):
    global toppage
    base_url = "https://api.hypixel.net/skyblock/auctions?page="
    with session.get(base_url + page) as response:
        # puts response in a dict
        data = response.json()
        toppage = data['totalPages']
        if data['success']:
            toppage = data['totalPages']
            for auction in data['auctions']:
                if not auction['claimed'] and auction['bin'] == True and not "Furniture" in auction[
                    "item_lore"]:  # if the auction isn't a) claimed and is b) BIN
                    # removes level if it's a pet, also
                    index = re.sub("\[[^\]]*\]", "", auction['item_name']) + auction['tier']
                    # removes reforges and other yucky characters
                    for reforge in REFORGES: index = index.replace(reforge, "")
                    # if the current item already has a price in the prices map, the price is updated
                    if index in prices:
                        if prices[index][0] > auction['starting_bid']:
                            prices[index][1] = prices[index][0]
                            prices[index][0] = auction['starting_bid']
                        elif prices[index][1] > auction['starting_bid']:
                            prices[index][1] = auction['starting_bid']
                    # otherwise, it's added to the prices map
                    else:
                        prices[index] = [auction['starting_bid'], float("inf")]

                    # if the auction fits in some parameters
                    if prices[index][1] > LOWEST_PRICE and prices[index][1] < HIGHEST_PRICE and prices[index][0] / \
                            prices[index][1] < LOWEST_PERCENT_MARGIN and auction['start'] + 60000 > now:
                        results.append([auction['uuid'], auction['item_name'], auction['starting_bid'], index])
        return data


async def get_data_asynchronous():
    # puts all the page strings
    pages = [str(x) for x in range(toppage)]
    with ThreadPoolExecutor(max_workers=10) as executor:
        with requests.Session() as session:
            loop = asyncio.get_event_loop()
            START_TIME = default_timer()
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch,
                    *(session, page)  # Allows us to pass in multiple arguments to `fetch`
                )
                # runs for every page
                for page in pages if int(page) < toppage
            ]
            for response in await asyncio.gather(*tasks):
                pass


def main():
    # Resets variables
    global results, searchableResults, prices, START_TIME
    START_TIME = default_timer()
    results = []
    searchableResults = []
    prices = {}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)

    # Makes sure all the results are still up to date
    if len(results): results = [[entry, prices[entry[3]][1]] for entry in results if (
            entry[2] > LOWEST_PRICE and entry[2] < HIGHEST_PRICE and prices[entry[3]][1] != float('inf') and
            prices[entry[3]][0] == entry[2] and prices[entry[3]][0] / prices[entry[3]][1] < LOWEST_PERCENT_MARGIN)]

    if len(results):  # if there's results to print

        if NOTIFY:
            notification.notify(
                title=max(results, key=lambda entry: entry[1])[0][1],
                message="Lowest BIN: " + f'{max(results, key=lambda entry: entry[1])[0][2]:,}' + "\nSecond Lowest: " + f'{max(results, key=lambda entry: entry[1])[1]:,}',
                app_icon=None,
                timeout=4,
            )

        df = pd.DataFrame(['/viewauction ' + str(max(results, key=lambda entry: entry[1])[0][0])])
        df.to_clipboard(index=False,
                        header=False)  # copies most valuable auction to clipboard (usually just the only auction cuz very uncommon for there to be multiple

        done = default_timer() - START_TIME
        if op: winsound.Beep(500, 500)  # emits a frequency 500hz, for 500ms
        for index, result in enumerate(results):
            # searchableResults.append([result[0][0], result[0][1]])
            searchableResults.append(result[0])
            # print(str(index) + ": Auction UUID: " + str(result[0][0]) + " | Item Name: " + str(result[0][1]) + " | Item price: " + Fore.GREEN + "{:,}".format(result[0][2]) + Style.RESET_ALL, " | Second lowest BIN: {:,}".format(result[1]) + " | Time to refresh AH: " + str(round(done, 2)))
            print(str(index) + ": Item Name: " + str(result[0][1]) + " | Item price: " + Fore.GREEN + "{:,}".format(
                result[0][2]) + Style.RESET_ALL,
                  " | Second lowest BIN: " + Fore.RED + "{:,}".format(result[1]) + Style.RESET_ALL)
        # print("\nLooking for auctions...")


print("Looking for auctions...")
main()

searching_points = 0


def dostuff():
    global now, toppage, searching_points

    # print("\nif " + str(time.time()/1000) + " > " + str(now/100000))
    # print("Own difference: \n")
    # print(time.time()/1000 - (now/100000))
    # print("\nif " + str(time.time()) + " > " + str(now))
    # print("\nif " + str(time.time()*1000) + " > " + str(now + 60000))
    # print("\n")
    # print(time.time()*1000 - (now + 60000))
    # print(round(((time.time()*1000 - (now + 60000)) / 1000)))
    # print(" --- ")
    # print(time.time()*1000 - (now + 60))

    looking_in_seconds = (round(((time.time() * 1000 - (now + 60000)) / 1000))) * -1
    if looking_in_seconds >= 0:
        print("Looking in " + str(looking_in_seconds) + " seconds", end="\r")
    else:
        print("Searching" + "." * searching_points + "                    ", end="\r")
        if searching_points < 3:
            searching_points = searching_points + 1
        else:
            searching_points = 0

    # if 60 seconds have passed since the last update
    if time.time() * 1000 > now + 60000:
        prevnow = now
        now = float('inf')
        c = requests.get("https://api.hypixel.net/skyblock/auctions?page=0").json()
        if c['lastUpdated'] != prevnow:
            now = c['lastUpdated']
            toppage = c['totalPages']
            main()
        else:
            now = prevnow
    time.sleep(0.25)


thread = threading.Thread(target=listen_to_keypresses, args=())
thread.daemon = True
thread.start()

while True:
    dostuff()
