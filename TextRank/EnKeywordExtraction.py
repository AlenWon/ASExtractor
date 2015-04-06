#-*- encoding:utf-8 -*-
import networkx as nx
import numpy as np
import collections
import re
from EnSegmentation import EnSegmentation

import sys
reload(sys)
sys.setdefaultencoding('utf8')

class EnKeywordExtraction(object):
	"""docstring for EnKeywordExtraction"""
	def __init__(self, stop_words_file=None):
		super(EnKeywordExtraction, self).__init__()
		self.text = ''
		self.tag_text = None
		self.keywords = []
		self.seg = EnSegmentation(stop_words_file=stop_words_file) 
		self.word_index = {}
		self.index_word = {}
		self.graph = None
		self.words_no_filter = None
		self.words_no_stop_words = None 
		self.words_all_filters = None
		self.firstSen = []
		self.counter = None

	def combine(self, word_list,window = 2):
		if window < 2:  
			window = 2
		for x in xrange(1,window):
			if x >= len(word_list):
				break
			word_list2 = word_list[x:]
			result = zip(word_list,word_list2)
			for res in result:
				yield res

	def train(self, text, window = 2, lower = False, with_tag_filter = True, vertex_source = 'all_filters', edge_source = 'no_stop_words'):
		self.text = text
		(_, 
		self.words_no_filter, 
		self.words_no_stop_words, 
		self.words_all_filters) = self.seg.segment(text=text, lower=lower, with_tag_filter=with_tag_filter)
		self.tag_text = self.get_tag(text)

		self.firstSen = self.words_no_stop_words[0]
		self.counter = collections.Counter(re.findall( '\w+' ,self.text))

		if vertex_source == 'no_filter':
			vertex_source = self.words_no_filter
		elif vertex_source == 'no_stop_words':
			vertex_source = self.words_no_stop_words
		else:
			vertex_source = self.words_all_filters

		if edge_source == 'no_filter':
			edge_source = self.words_no_filter
		elif edge_source == 'no_stop_words':
			edge_source = self.words_no_stop_words
		else:
			edge_source = self.words_all_filters
		#构造节点
		index = 0
		for words in vertex_source:
			for word in words:
				if not self.word_index.has_key(word.lower()):
					self.word_index[word.lower()] = index
					self.index_word[index] = word.lower()
					index += 1

		#构造图
		words_number = index
		self.graph = np.zeros((words_number,words_number)) #matrix

		#构造边
		for word_list in edge_source:
			for w1,w2 in self.combine(word_list,window):
				if not self.word_index.has_key(w1):
					continue
				if not self.word_index.has_key(w2):
					continue
				index1 = self.word_index[w1]
				index2 = self.word_index[w2]
				w = self.get_edge_weight(w1,w2)
				#print w1,w2,": ",w
				self.graph[index1][index2] = w
				self.graph[index2][index1] = w
		#使用networkx库的pagerank算法		
		nx_graph = nx.from_numpy_matrix(self.graph)
		scores = nx.pagerank(nx_graph)

		#对各词得分进行排序
		sorted_scores = sorted(scores.items(),key = lambda item: item[1], reverse = True)
		for index,_ in sorted_scores:
			self.keywords.append(self.index_word[index])
			#print self.index_word[index],_

	def get_edge_weight(self,word1,word2,a = 0.8, b = 0.1, c = 0.1):
		'''
			w(vi,vj) = a*1 + b*[tf(word1)+tf(word2)] + c*IsHeadSen(w1,w2)
		'''
		weight = 0
		is_w1 = 0
		is_w2 = 0
		tf_w1 = self.counter[word1]
		tf_w2 = self.counter[word2]
		if word1 in self.firstSen:
			is_w1 = 1
		if word2 in self.firstSen:
			is_w2 = 1
		weight = a + b*(tf_w1 + tf_w2) + c*(is_w1 + is_w2)
		return weight
		
	def get_keyphrases(self, article_type='Abstract'):
		if article_type == 'Abstract':
			aThird = len(self.keywords)
		elif article_type == 'Fulltext': 
			aThird = len(self.keywords)/3
		keyphrases = self.keywords[0:aThird]
		#print keyphrases
		modifiedKeyphrases = []
		dealtWith = set([]) #keeps track of individual keywords that have been joined to form a keyphrase

		#textlist = self.words_no_filter
		#print self.words_no_filter
		
		for textlist in self.words_no_filter:
			i = 0
			j = 1
			while j < len(textlist):
				firstWord = textlist[i]
				secondWord = textlist[j]
				#print firstWord,"&",secondWord
				k = j+1
				if k < len(textlist):
					thirdWord = textlist[k]
					if firstWord in keyphrases and secondWord in keyphrases and thirdWord in keyphrases:
						keyphrase = firstWord + ' ' + secondWord + ' '+ thirdWord
						#print '1:',keyphrase
						if keyphrase not in modifiedKeyphrases:
							modifiedKeyphrases.append(keyphrase)
						dealtWith.add(firstWord)
						dealtWith.add(secondWord)
						dealtWith.add(thirdWord)
						i = i+2
						j = j+2
					elif firstWord in keyphrases and secondWord in keyphrases:
						keyphrase = firstWord + ' ' + secondWord
						#print '2:',keyphrase 
						if keyphrase not in modifiedKeyphrases:
							modifiedKeyphrases.append(keyphrase)
						dealtWith.add(firstWord)
						dealtWith.add(secondWord)
						i = i + 1
						j = j + 1
						continue
				elif firstWord in keyphrases and secondWord in keyphrases:
					keyphrase = firstWord + ' ' + secondWord
					#print '3:',keyphrase
					if keyphrase not in modifiedKeyphrases:
						modifiedKeyphrases.append(keyphrase)
						dealtWith.add(firstWord)
						dealtWith.add(secondWord)
				else:
					if firstWord in keyphrases and firstWord not in dealtWith :
						#for w in self.tag_text:
						# 	if w[0] == firstWord and w[1] == 'NNP' and firstWord not in modifiedKeyphrases:
						if firstWord not in modifiedKeyphrases:
							modifiedKeyphrases.append(firstWord)
							dealtWith.add(firstWord)
						
					if j == len(textlist)-1 and secondWord in keyphrases and secondWord not in dealtWith:
						#for w in self.tag_text:
						# 	if w[0] == secondWord and w[1] == 'NNP' and secondWord not in modifiedKeyphrases:
						 		#print secondWord
						 if secondWord not in modifiedKeyphrases:
							modifiedKeyphrases.append(secondWord)
							dealtWith.add(secondWord)					
				i = i + 1
				j = j + 1
		return modifiedKeyphrases

	def get_keyphrases_maximal(self,article_type='Abstract'):
		if article_type == 'Abstract':
			#aThird = len(self.keywords)
			aThird = 20
		elif article_type == 'Fulltext': 
			aThird = len(self.keywords)/3
		keyphrases = self.keywords[0:aThird]
		#print keyphrases
		#print self.words_no_filter
		modifiedKeyphrases = []
		dealtWith = set([]) #keeps track of individual keywords that have been joined to form a keyphrase
		for textlist in self.words_no_filter:
			i = 0 
			while i < len(textlist):
				firstWord = textlist[i]
				if firstWord.lower() in keyphrases:
					phrase = firstWord
					j = i+1
					while j < len(textlist):
						if textlist[j].lower() in keyphrases:
							phrase += ' '+textlist[j]
							j += 1
						else:
							break
					if phrase not in modifiedKeyphrases and j-i>1:   #bigram
						modifiedKeyphrases.append(phrase)
					i = j+1
				else:
					i += 1
		num = len(self.keywords)/3 + 1
		return modifiedKeyphrases

	def get_tag(self,text):
		return self.seg.get_tag_text(text)


if __name__ == '__main__':

	text = open('../text/008.txt','r+').read()
	keyword = EnKeywordExtraction(stop_words_file='./trainer/stopword_en.data')
	keyword.train(text=text,with_tag_filter=True)
	print keyword.firstSen
	#print keyword.words_no_filter
	print keyword.get_keyphrases_maximal()
	#word_tag =  keyword.get_tag(text)
	#print word_tag
	#for w in word_tag:
	#	if w[1] == 'VBN':
	#		print w