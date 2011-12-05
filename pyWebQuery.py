#!/usr/bin/python
# -*- coding: utf-8 -*-   
#version 0.1

from BeautifulSoup import BeautifulSoup
import urllib2,urllib,cookielib,urlparse
import os,sys
import re
cookieJar = cookielib.LWPCookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
urllib2.install_opener(opener) 

defaultHeader = {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}  
def setHeader(header):
    global defaultHeader
    defaultHeader = header
verbose = True
def _i(string):
    """print string in verbose mode 
    Arguments:
    - `string`:
    """
    if verbose:
        print string

def hasWords(string,words):
    for item in words:
        if not (item in string):
            return False
    else:
        return True
def hasOneWords(string,words):
    for item in words:
        if item in string:
            return True
    return False
#WARNINGTAG: don't forget BadMoveException
class Page(object):
    """Page is used for holding page content to further obtain DOM Element.
    
    """
    
    def _fetchHTML(self,url,referer="http://www.google.com/"):
        """fetch HTML in UTF-8 encoding
        
        Arguments:
        - `url`:
        - `refer`:default referer is google.com
        """
        global defaultHeader
        headers = defaultHeader.copy()
        if referer!=None:
            headers['Referer'] = referer
        req = urllib2.Request(url,headers = headers) 
        print headers
        return urllib2.urlopen(req).read()

    def _postAndFetchHTML(self,url,postData,referer="http://www.google.com"):
        """post data and fetch returnning html
        
        Arguments:
        - `self`:
        - `url`:
        - `referer`:
        """
        global defaultHeader
        headers = defaultHeader.copy()
        if referer!=None:
            headers["Referer"] = referer
        req = urllib2.Request(url,urllib.urlencode(postData),headers)
        return urllib2.urlopen(req).read()

    def __init__(self, URL=None,HTML=None,prevPage=None,nextPage=None):
        """
        Arguments:
        - `URL`:current URL
        - `HTML`:initHTML
        - `prevPage`:this page comes from previous PageObject
        - `nextPage`:this page comeback from next PageObject
        """
        self._URL = URL
        self._HTML = HTML
        self._prevPage = prevPage
        self._nextPage = nextPage
        self._postData = None
        if prevPage!= None:
            self._referer = prevPage._URL
        else:
            self._referer = None
        #has URL and no HTML means create by goto or from new URL,so here we fetch the HTML 
        if self._HTML == None and self._URL!=None:
            self._HTML = self._fetchHTML(self._URL,self._referer)

    def goto(self,URL):
        """goto some Page from this Page
        
        Arguments:
        - `self`:
        - `URL`:where to go
        """
        URL = urlparse.urljoin(self._URL,URL)
        self._nextPage = Page(URL=URL,prevPage = self)
        return self._nextPage

    def post(self,URL,postData):
        """post parameters from this Page return a new Page Object hold the returning HTML
        
        Arguments:
        - `self`:
        - `URL`:
        - `parameters`:POSTDATA
        - `referer`:
        """        
        URL = urlparse.urljoin(self._URL,URL)
        newPage = Page(URL = URL,prevPage=self,
                       HTML = self._postAndFetchHTML(URL,postData=postData,referer=self._referer))
        newPage._postData = postData
        return newPage

    def forward(self):
        """goto where it backs from,throw BadMoveException no futher forward
        
        Arguments:
        - `self`:
        """
        return self._nextPage

    def backward(self):
        """goto where it comes from,throw BadMoveException is nofurther backward
        
        Arguments:
        - `self`:
        """
        return self._prevPage 

    def refresh(self):
        """refresh this page 

        Arguments:
        - `self`:
        """
        if self._postData == None:
            self._HTML = self._fetchHTML(self._URL)
        else:
            self._HTML = self._postAndFetchHTML(self._URL,self._postData,self._referer)
    def find(self,selectors):
        """find the css specified DOM sets
        
        Arguments:
        - `self`:
        - `selector`:basic css selector support
        """
        return Query(self,selectors)


class PageSet(list):
    """a collection of Pages from
    """
    
    def __init__(self):
        pass
    
    def find(self,selectors):
        querySet = QuerySet()
        for page in self:
            querySet.append(page.find(selectors))
        return querySet

class Query(object):
    """Action to filter dom or and do some action indicate by dom or page
    """
    def _filterDOM(self,HTML,selectors): 
        soup = BeautifulSoup(HTML)
        return self._filterSoup(soup,selectors)

    def _filterSoup(self,soup,selectors): 
        token="#. :" 
        filters = [] 
        i=0
        j=0
        for i in range(len(selectors)):
            if selectors[i] in token:
                continue
            elif i > 0 and selectors[i-1] in token:
                selectorType=selectors[i-1]
                j = i
                if len(selectors)==i+1 or  selectors[i+1] in token: 
                    filters.append({"selectorType":selectorType,
                                    "selectorValue":selectors[j:i+1]})
                
            elif len(selectors)==i+1 or  selectors[i+1] in token:
                if j-1 >= 0:
                    selectorType = selectors[j-1]
                else:
                    selectorType = " "
                filters.append({"selectorType":selectorType,
                                "selectorValue":selectors[j:i+1]})
            else:
                continue
        typeMap = {"#":"id",
                   ".":"class",
                   }
        for item in filters:
            if item["selectorType"] == " ":
                soupResult = soup.findAll(item["selectorValue"])
            elif item["selectorType"] == ":":
                content = item["selectorValue"]
                goodSelectorType = content[0:content.index("[")]
                goodSelectorValue = content[content.index("[")+1:-1]
                soupResult = self._advancedFilter(soup,goodSelectorType,goodSelectorValue)
            else:
                soupResult = soup.findAll(attrs={typeMap[item["selectorType"]]:item["selectorValue"]})
            soup = BeautifulSoup(str(soupResult))
        return soupResult
    def _advancedFilter(self,soup,selectorType,selectorValue):
        
        keywords = selectorValue.split("&")
        if selectorType == "text": 
            return soup.findAll(lambda tag:hasWords("".join(tag.findAll(text=True)),keywords))
        else:# selectorType == "src" or selectorType == "href" or selectorType == "title":
            return soup.findAll(lambda tag:tag.has_key(selectorType) and hasWords(tag[selectorType],keywords))
        
    def _download(self,url,path=None,referer="www.google.com"):
        if path!=None:
            para = "-O \"%s\"" % path
        else:
            para = ""
        cmd = """wget "%s" -nc %s --header="Referer:%s"  """ %(url,para,referer)
        os.system(cmd)
    def __init__(self,Page,selectors,soup=None):
        """
        
        Arguments:
        - `Page`: Query from which page
        """
        self._Page = Page
        if soup == None:
            #come from Page
            self._soupResult = self._filterDOM(self._Page._HTML,selectors)
        else:
            #come from Query,may because of using find two times
            self._soupResult = self._filterSoup(soup,selectors)

    def __len__(self):
        return len(self._soupResult)
    
    def __getitem__(self,i):
        return self._soupResult[i]
    
    def find(self,selectors):
        return Query(self._Page,selectors,BeautifulSoup(str(self._soupResult)))
    
    def follow(self,keyword="*"):
        
        soupResult = BeautifulSoup(str(self._soupResult)).findAll(lambda tag:tag.has_key("href") and (keyword=="*" or keyword in tag["href"]))
        baseURL = self._Page._URL
        pageSet = PageSet()
        for item in soupResult:
            targetURL = urlparse.urljoin(baseURL,item["href"])
            _i("follow page %s" % targetURL)
            pageSet.append(self._Page.goto(targetURL))
        return pageSet
    def download(self,keyword="*",fileNameGenerator = None,directAddress = None):
        if directAddress!=None:
            try:
                self._download(directAddress,referer=self._Page._URL)
            except Exception,e:
                return 0
            return 1
        soupResult = BeautifulSoup(str(self._soupResult)).findAll(lambda tag:tag.has_key("href") and (keyword=="*" or keyword in tag["href"]))
        baseURL = self._Page._URL
        pageSet = PageSet()
        counter = 0
        for item in soupResult:
            targetURL = urlparse.urljoin(baseURL,item["href"])
            if fileNameGenerator!=None:
                name = fileNameGenerator.next()
            else:
                name = None
            self._download(targetURL,path=name,referer=self._Page._URL)
            counter+=1
        return counter
    def attr(attrName):
        results = self._soupResult.findAll(lambda tag:tag.has_key(attrName))
        return [item[attrName] for item in results]

    def downloadSrc(self,keyword="*",fileNameGenerator = None):
        soupResult = BeautifulSoup(str(self._soupResult)).findAll(lambda tag:tag.has_key("src") and keyword=="*" or keyword in tag["src"])
        baseURL = self._Page._URL
        pageSet = PageSet()
        counter = 0
        for item in soupResult:
            targetURL = urlparse.urljoin(baseURL,item["src"])
            if fileNameGenerator!=None:
                name = fileNameGenerator.next()
            else:
                name = None
            self._download(targetURL,path=name,referer=self._Page._URL)
            counter+=1
        return counter
class QuerySet(list):
    """a collection of QuerySet
    """
    
    def __init__(self):
        pass
    def __len__(self):
        counter = 0
        for item in self:
            counter += len(item)
        return counter
    def __getitem__(self,index):
        counter = 0
        for item in self:
            if index >=counter and index < len(item)+counter:
                return item[index-counter]
            counter+=len(item)
        else:
            raise IndexError
        
    def find(self,selectors):
        """find match DOM in the current querys
        
        Arguments:
        - `self`:
        - `selectors`:
        """
        querySet = QuerySet()
        for item in self:
            querySet.append(item.find(selectors))
        return querySet
    
    def follow(self,keyword="*"):
        pageSet = PageSet()
        for item in self: 
            pageSet.extend(item.follow(keyword))
        return pageSet
    def download(self,keyword="*",fileNameGenerator = None):
        counter = 0
        for item in self:
            counter += item.download(keyword,fileNameGenerator)
        return counter
    def downloadSrc(self,keyword="*",fileNameGenerator = None):
        counter = 0
        for item in self:
            counter += item.downloadSrc(keyword,fileNameGenerator)
        return counter
