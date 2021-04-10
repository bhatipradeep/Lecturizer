#Flask-App
#Libraries for video-audio handling and Speech to Text conversion
from flask import Flask, render_template, request, redirect, send_file
import speech_recognition as sr
from moviepy.editor import AudioFileClip
from werkzeug.utils import secure_filename
import wave, math, contextlib
import os
import DocMaker
import docx

#Libraries for generating summary of a report
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx

#Libraries from tfidf.py
from nltk import tokenize
from operator import itemgetter
import math
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize 

from tfidf import check_sent, get_top_n, tf_idf

#Function to split the report into sentences
def read_article(file_name):
    file = open(file_name, "r")
    filedata = file.readlines()
    article = filedata[0].split(". ")
    sentences = []

    for sentence in article:
        #print(sentence)
        sentences.append(sentence.replace("[^a-zA-Z]", " ").split(" "))
    sentences.pop() 
    
    return sentences

#Function to calculate cosine similarity between a pair of sentences
def sentence_similarity(sent1, sent2, stopwords=None):
    if stopwords is None:
        stopwords = []
 
    sent1 = [w.lower() for w in sent1]
    sent2 = [w.lower() for w in sent2]
 
    all_words = list(set(sent1 + sent2))
 
    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)
 
    # build the vector for the first sentence
    for w in sent1:
        if w in stopwords:
            continue
        vector1[all_words.index(w)] += 1
 
    # build the vector for the second sentence
    for w in sent2:
        if w in stopwords:
            continue
        vector2[all_words.index(w)] += 1
 
    return 1 - cosine_distance(vector1, vector2)

#Function to build the similarity matrix of all pairs of sentences
def build_similarity_matrix(sentences, stop_words):
    # Create an empty similarity matrix
    similarity_matrix = np.zeros((len(sentences), len(sentences)))
 
    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2: #ignore if both are same sentences
                continue 
            similarity_matrix[idx1][idx2] = sentence_similarity(sentences[idx1], sentences[idx2], stop_words)

    return similarity_matrix

# Function to convert list of strings to string
def listToString(s): 
    
    # initialize an empty string
    str1 = " " 
    
    # return string  
    return (str1.join(s))

#Function to generate the summary of report using all the util functions
def generate_summary(file_name):
    stop_words = stopwords.words('english')
    summarize_text = []

    # Step 1 - Read text anc split it
    sentences =  read_article(file_name)

    # Step 2 - Generate Similary Martix across sentences
    sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)

    # Step 3 - Rank sentences in similarity martix
    sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
    scores = nx.pagerank(sentence_similarity_graph)

    # Step 4 - Sort the rank and pick top sentences
    ranked_sentence = sorted(((scores[i],s) for i,s in enumerate(sentences)), reverse=True)    
    #print("Indexes of top ranked_sentence order are ", ranked_sentence)    

    #Choosing top 25% sentences for summary
    percent_summary = 0.4
    top_n = int(percent_summary*len(sentences)) 

    for i in range(top_n):
      summarize_text.append(" ".join(ranked_sentence[i][1]))

    summarytxt = ".\n".join(summarize_text)

    #Writing the summary into summary.txt file
    fo = open("summary.txt", "a")
    fo.write(summarytxt + ".")
    fo.close()

    return summarytxt

app = Flask(__name__)

docs = DocMaker.DocMaker("lol")

@app.route("/", methods=["GET", "POST"])
def index():
    #If a POST request is received
    if request.method == "POST":

        #If file not found in the request, redirect
        if "file" not in request.files:
            return redirect(request.url)

        f = request.files["file"]
        if f.filename == "":
            return redirect(request.url)

        if f:
            #File paths for saving video and audio (wav) files 
            fpath = os.path.join(r"video-audio-data/", secure_filename(f.filename))
            wavpath = "video-audio-data/temp.wav"
            
            docs.file_name = f.filename

            #Saving video file temporarily
            f.save(fpath)

            #Extracting audio from video and saving the extracted wav file
            audioclip = AudioFileClip(fpath)
            audioclip.write_audiofile(wavpath)

            #Dividing whole audio file into chunks to calculate the number of frames 
            with contextlib.closing(wave.open(wavpath,'r')) as fr:
                frames = fr.getnframes()
                rate = fr.getframerate()
                duration = frames / float(rate)

            #Chunk size in seconds
            chunksize = 7
            total_duration = math.ceil(duration / chunksize)

            #using Google's Speech Recognition API, 
            r = sr.Recognizer()

            #Removing older transcription and summary, if they exist            
            if os.path.exists("transcription.txt"):
                os.remove("transcription.txt")
            if os.path.exists("summary.txt"):
                os.remove("summary.txt")
            
            transtr = ""

            #Converting each chunk into text and adding it to the transcription file
            for i in range(0, total_duration):
                with sr.AudioFile(wavpath) as source:
                    audio = r.record(source, offset=i*chunksize, duration=chunksize)
                fo = open("transcription.txt", "a")
                fo.write(r.recognize_google(audio))
                transtr = transtr + r.recognize_google(audio) + ". "
                fo.write(". ")
            fo.close()

            docs.add_transcription(transtr)

            transsum = generate_summary("transcription.txt")

            docs.add_summary(transsum)
            docs.add_imp_words(tf_idf(transtr))

            #Removing temporary video and sound files
            os.remove(wavpath)
            os.remove(fpath)  

    return render_template('index.html')

@app.route('/return-file')
def return_file():
    return send_file("summary.txt", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, threaded=True)