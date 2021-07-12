#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  6 00:40:25 2021

@author: luochengwen
"""
from collections import Counter
class Solution():
    def findMaxForm(self, strs, m, n):
        """
        :type strs: List[str]
        :type m: int
        :type n: int
        :rtype: int
        """
        str_len = len(strs)
        def check_list(sublist):
            full_str = "".join(sublist)
            ful_count = Counter(full_str)
            if ful_count["0"] > m or ful_count["1"] > n:
                return False
            return True

        def dfs(input_list, pos):
            if check_list(input_list):
                max_len.append(len(input_list))
            else:
                return
            for each in range(pos, str_len):
                input_list.append(strs[each])
                dfs(input_list, each + 1)
                input_list.pop()
        max_len = []
        for pos_x in range(str_len):
            dfs([strs[pos_x]], pos_x + 1)
        return max(max_len)
   
import requests
from bs4 import BeautifulSoup
import random
from time import sleep
def scrapeWikiArticle(url):
    response = requests.get(
        url = url,
        )
    soup = BeautifulSoup(response.content, "html.parser")
    
    title = soup.find(id = "firstHeading")
    print(title.text)
    contenttext = soup.find
    sleep(3)
    
    allLinks = soup.find(soup.find)
    
    
   
    
   
import requests
from bs4 import BeautifulSoup
import random
from time import sleep
def scrapeWikiArticle(url):
	response = requests.get(
		url=url,
	)
	
	soup = BeautifulSoup(response.content, 'html.parser')

	title = soup.find(id="firstHeading")
	print(title.text)

	allLinks = soup.find(id="bodyContent").find_all("a")
	random.shuffle(allLinks)
	linkToScrape = 0
    
	for link in allLinks:
		# We are only interested in other wiki articles
		if link['href'].find("/wiki/") == -1: 
			continue

		# Use this link to scrape
		linkToScrape = link
		break

	scrapeWikiArticle("https://en.wikipedia.org" + linkToScrape['href'])


scrapeWikiArticle("https://en.wikipedia.org/wiki/China")

#to collect the text
text = ''
for paragraph in soup.find_all('p'):
    text += paragraph.text


#to clean up the text
text = re.sub(r'\[.*?\]+', '', text)
text = text.replace('\n', '')


class TreeNode(object):
    def __init__(self, val = 0, left = None, right = None):
        self.val = val
        self.left = left
        self.right = right

import copy

class Solution():
    def generateTrees(self, n):
        nums = [[None] for _ in range(n+1)]
        nums[1] = [TreeNode(1)]
        def modify_val(root, modify):
            if not root:
                return None
            temp = copy.copy(root)
            temp.val = root.val + modify
            temp.left = modify_val(root.left, modify)
            temp.right = modify_val(root.right, modify)
            return temp
        if n == 1:
            return nums[1]
        for i in range(2, n+1):
            nums[i] = []
            for j in range(i):
                for k in nums[j]:
                    for l in nums[i-1-j]:
                        new = TreeNode(j+1)
                        new.left = k
                        new.right = modify_val(l, j+1)
                        if new:
                            nums[i].append(new)
                            print(new.val)
        return nums[n]
        
            
class Solution():
    def isInterleave(self, s1, s2, s3):
        """
        :type s1: str
        :type s2: str
        :type s3: str
        :rtype: bool
        """
        len1 = len(s1)
        len2 = len(s2)
        len3 = len(s3)

        if len3 == 0:
            if len1 == 0 and len2 == 0:
                return True
            else:
                return False
        elif len1 == 0:
            return s2 == s3
        elif len2 == 0:
            return s1 == s3
        
        dp = [[False] * (len1 + 1) for _ in range(len2 + 1)]
        dp[0][0] = True
        flg, p_1, p_2, p_3 = 0, 0, 0, 0
        while p_1 < len1 or p_2 < len2:
            if flg == 0:
                if p_1 == len1:
                    break
                while p_1 < len1 and s1[p_1] == s3[p_3]:
                    dp[p_2][p_1 + 1] = dp[p_2][p_1]
                    p_1 += 1
                    p_3 += 1
                flg = 1
                print(dp)
            if flg == 1:
                print("p2", p_2)
                print("p3", p_3)
                if p_2 == len2:
                    break
                while p_2 < len2 and s2[p_2] == s3[p_3]:
                    dp[p_2 + 1][p_1] = dp[p_2][p_1]
                    p_2 += 1
                    p_3 += 1
                flg = 0
        print(dp)
        return dp[-1][-1]

class Solution():
    def maxProduct(self, nums):
        """
        :type nums: List[int]
        :rtype: int
        """
        import numpy
        len_n = len(nums)
        dp = [x for x in nums]

        for x in range(len_n):
            for y in range(x + 1, len_n + 1):
                print(nums[x:y])
                dp[x] = max(dp[x], numpy.prod(nums[x:y]))
                print(dp)
        return max(dp)
    
    
    
    
    
    
from __future__ import with_statement
import contextlib
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
try:
    from urllib.request import urlopen
except ImportError:
    from urllib3 import urlopen
import sys

def make_tiny(url):
    request_url = ('http://tinyurl.com/api-create.php?' + 
                   urlencode({'url':url}))
    with contextlib.closing(urlopen(request_url)) as response:
        return response.read().decode('utf-8')
    
def main():
    for tinyurl in map(make_tiny, sys.argv[1:]):
        print(tinyurl)
        
if __name__ == '__main__':
    main()
    
    







    
    
    
    
    