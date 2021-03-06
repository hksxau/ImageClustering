#!/usr/bin/python

import sys, getopt
import os
import cv2
import numpy as np
import siftLib
import surfLib
import fastDetector
import starDetector
import randomDetector
import orbLib
import briefDescriptor
import freakDescriptor
import KMeans1
import histogram
import tfidf
import tfidf2
import tfnorm
import tfidfnorm
import time
import datetime
import Dbscan
import Birch
import hierarchicalClustering
import hierarchicalClustScipy
import minibatch
import meanSift
import randomSamplesBook
import allrandom
from sklearn import metrics
import simpleBinarization
import filterMin
import filterMax
import filterMaxMin
import okapi
import sampleKeypoints
import sampleAllKeypoints
#import warnings
import statistics
import xlsxwriter
import cv
import communityDetection
import powerNorm
import evaluationUsers

def get_imlist(path):  
   paths = []
   files = []
   for f in os.listdir(path):
      if 'DS_Store' not in f:
	 paths.append(os.path.join(path,f))
	 files.append(int(f.split('_')[-1].split('.')[0]))

   files,paths = zip(*sorted(zip(files, paths)))
   return paths
   
def run(pathImages,method,numpatch,imsample,percentage,codebook,dist,size,fselec,fselec_perc,histnorm,clust,nclusters,rep):

   #################################################################
   #
   # Initializations and result file configurations
   #
   #################################################################   
      
   im_dataset_name= pathImages.split('/')[-1]
   
   date_time = datetime.datetime.now().strftime('%b-%d-%I%M%p-%G')
   
   name_results_file = 'BOC_' + im_dataset_name + '_' + str(numpatch) + '_' + imsample + '_' + codebook + '_' + str(size) + '_' + fselec + '_' + histnorm + '_' + clust + '_'+ dist + '_' + date_time
   
   #dir_results = 'Results_' + im_dataset_name + '_BOC_' + date_time
   dir_results = 'Results_BOC'
   
   if not os.path.exists(dir_results):
      os.makedirs(dir_results)  
      
   file_count = 2
   file_name = os.path.join(dir_results,name_results_file)
   while os.path.exists(file_name + ".txt"):
      file_name = os.path.join(dir_results,name_results_file) + "_" + str(file_count)
      file_count = file_count + 1
   f = open(file_name + ".txt", 'w')
   
   #################################################################
   #
   # Get images
   #
   #################################################################
   
   #pathImages = '/Users/Mariana/mieec/Tese/Development/ImageDatabases/Graz-01_sample'
   
   imList = get_imlist(pathImages)
   
   print 'Number of images read = ' + str(len(imList))
   f.write("Number of images in dataset read: " + str(len(imList)) + "\n")
   
   #################################################################
   #
   # Image description
   #
   #################################################################
      
   kp_vector = [] #vector with the keypoints object
   des_vector = [] #vector wih the descriptors (in order to obtain the codebook)
   number_of_kp = [] #vector with the number of keypoints per image
      
   counter = 1
      
   #save current time
   start_time = time.time()   
   
   labels = []
   class_names = []   
   
   #ADDED
   imPaths = []   
   
   #number of divisions of the image 
   div = int(np.sqrt(numpatch))
   
   n_images = 0
   #detect the keypoints and compute the sift descriptors for each image
   for im in imList:
      if 'DS_Store' not in im:
	 #ADDED
	 imPaths.append(im)	 
         print 'image: ' + str(im) + ' number: ' + str(counter)
         #read image
         img = cv2.imread(im,1)
	 img_gray = cv2.imread(im,0)
	 img_lab = cv2.cvtColor(img,cv.CV_BGR2Lab)
	 
	 height, width, comp = img_lab.shape
	 h_region = height/div
	 w_region = width/div	 
         
         des = []
	 for i in range(0,div):
	    for j in range(0,div):
	       
	       #mask
	       mask = np.zeros(img_gray.shape, dtype=np.uint8)
	       mask[i*h_region:(i+1)*h_region, j*w_region:(j+1)*w_region] = 1	       

	       hist = cv2.calcHist([img_lab],[0,1,2],mask,[256,256,256],[0,256,0,256,0,256])
        
	       max_color_l, max_color_a, max_color_b = np.where(hist == np.max(hist))
	       des.append([max_color_l[0], max_color_a[0], max_color_b[0]])        
         
         number_of_kp.append(div*div)
         if counter==1:
            des_vector = des
         else:
            des_vector = np.concatenate((des_vector,des),axis=0)
         counter += 1   
         
         #for evaluation
         name1 = im.split("/")[-1]
         name = name1.split("_")[0]
                 
         if name in class_names:
            index = class_names.index(name)
            labels.append(index)
         else:
            class_names.append(name)
            index = class_names.index(name)
            labels.append(index) 
	    
	 n_images = n_images + 1
            
   #measure the time to compute the description of each image (divide time elapsed by # of images)
   elapsed_time = (time.time() - start_time) / len(imList)
   print 'Time to compute detector and descriptor for each image = ' + str(elapsed_time)   
   
   f.write('Average time to compute detector and descriptor for each image = ' + str(elapsed_time) + '\n')
   
   average_words = sum(number_of_kp)/float(len(number_of_kp))
   
   print 'Total number of features = ' + str(len(des_vector)) 
   f.write('Total number of features obtained = ' + str(len(des_vector)) + '\n') 
   print 'Average number of keypoints per image = ' + str(average_words) 
   f.write('Average number of keypoints per image = ' + str(average_words) + '\n')
   
   #################################################################
   #
   # Image and Keypoint sampling
   #
   ################################################################# 
   
   rand_indexes = []
   nmi_indexes = []
   
   for iteraction in range(0,rep):
      
      print "\nIteraction #" + str(iteraction+1) + '\n'
      f.write("\nIteraction #" + str(iteraction+1) + '\n')
   
      print 'Sampling images and keypoints prior to codebook computation...'
      
      if imsample != "NONE":
         
         sampleKp = sampleKeypoints.SamplingImandKey(n_images, number_of_kp, average_words, percentage)
         sampleallKp = sampleAllKeypoints.SamplingAllKey(percentage)
         
         names_sampling = np.array(["SAMPLEI", "SAMPLEP"])
         sample_method = np.array([sampleKp, sampleallKp])   
         
         #Get the sampling method passed in the -g argument
         index = np.where(names_sampling==imsample)[0]
         if index.size > 0:
            sampling_to_use = sample_method[index[0]]
         else:
            print 'Wrong sampling method passed in the -g argument. Options: NONE, SAMPLEI, SAMPLEP'
            sys.exit()
            
         #FOR RESULTS FILE
         sampling_to_use.writeFile(f)
      
         des_vector_sampled = sampling_to_use.sampleKeypoints(des_vector)
            
         print 'Total number of features after sampling = ' + str(len(des_vector_sampled))
         f.write('Total number of features after sampling = ' + str(len(des_vector_sampled)) + '\n')
            
         print 'Images and keypoints sampled...'
         
      else:
         print 'No sampling method chosen'
         #FOR RESULTS FILE
         f.write("No method of keypoint sampling chosen. Use all keypoints for codebook construction \n")
         des_vector_sampled = des_vector
      
      #################################################################
      #
      # Codebook computation
      #
      #################################################################
   
      print 'Obtaining codebook...'
      
      #save current time
      start_time = time.time()   
      
      #Get detector classes
      codebook_kmeans = KMeans1.KMeans1(size)
      codebook_birch = Birch.Birch(size)
      codebook_minibatch = minibatch.MiniBatch(size)
      codebook_randomv = randomSamplesBook.RandomVectors(size)
      codebook_allrandom = allrandom.AllRandom(size)
      
      names_codebook = np.array(["KMEANS", "BIRCH", "MINIBATCH", "RANDOMV", "RANDOM"])
      codebook_algorithm = np.array([codebook_kmeans, codebook_birch, codebook_minibatch, codebook_randomv, codebook_allrandom])
      
      #Get the codebook algorithm passed in the -c argument
      index = np.where(names_codebook==codebook)[0]
      if index.size > 0:
         codebook_to_use = codebook_algorithm[index[0]]
      else:
         print 'Wrong codebook construction algorithm name passed in the -c argument. Options: KMEANS, MINIBATCH, RANDOMV and RANDOM'
         sys.exit()   
         
      #FOR RESULTS FILE
      codebook_to_use.writeFileCodebook(f)
         
      #Get centers and projections using codebook algorithm
      ceters, projections = codebook_to_use.obtainCodebook(des_vector_sampled,des_vector)
      
      elapsed_time = (time.time() - start_time)
      print 'Time to compute codebook = ' + str(elapsed_time)   
      f.write('Time to compute codebook = ' + str(elapsed_time) +'\n')
      
      #################################################################
      #
      # Obtain Histogram
      #
      #################################################################   
   
      print 'Obtaining histograms...'
      
      #print 'projection shape = '+ str(projections.shape)
      #print 'size = ' + str(size)
      #print 'n of images = ' + str(n_images)
      #print 'number of kp' + str(number_of_kp)
      
      hist = histogram.computeHist(projections, size, n_images, number_of_kp)
      print hist 
      print 'Histograms obtained'
      
      ################################################################
      #
      # Feature selection
      #
      #################################################################  
      
      print 'Number of visual words = '+str(len(hist[0]))
      
      if fselec != "NONE":
         
         print 'Applying feature selection to descriptors...'
         
         filter_max = filterMax.WordFilterMax(fselec_perc[0])
         filter_min = filterMin.WordFilterMin(fselec_perc[1])
         filter_maxmin = filterMaxMin.WordFilterMaxMin(fselec_perc[0], fselec_perc[1])
         
         names_filter = np.array(["FMAX", "FMIN", "FMAXMIN"])
         filter_method = np.array([filter_max, filter_min, filter_maxmin])
            
         #Get the feature selection method passed in the -f argument
         index = np.where(names_filter==fselec)[0]
         if index.size > 0:
            filter_to_use = filter_method[index[0]]
         else:
            print 'Wrong codebook construction algorithm name passed in the -f argument. Options: NONE, FMAX, FMIN, FMAXMIN'
            sys.exit()      
         
         hist = filter_to_use.applyFilter(hist,size,n_images)
         
         #FOR RESULTS FILE
         filter_to_use.writeFile(f)
            
         new_size = hist.shape[1]
         
         print 'Visual words Filtered'
         print 'Number of visual words filtered = '+str(size-new_size)
         f.write("Number of visual words filtered = " + str(size-new_size) + '\n')
         print 'Final number of visual words = '+str(new_size)
         f.write('Final number of visual words = '+str(new_size) + '\n')
         
      else:
         #FOR RESULTS FILE
         filter_min = filterMin.WordFilterMin(0)
         hist = filter_min.applyFilter(hist,size,n_images)
         new_size = hist.shape[1]
         print 'Number of visual words filtered = '+str(size-new_size)
         f.write("No feature selection applied \n")
      
      #################################################################
      #
      # Histogram Normalization
      #
      #################################################################      
      
      if histnorm != "NONE":
         
         #Get detector classes
         norm_sbin = simpleBinarization.SimpleBi()
         norm_tfnorm = tfnorm.Tfnorm()
         norm_tfidf = tfidf.TfIdf()
         norm_tfidf2 = tfidf2.TfIdf2()
         norm_tfidfnorm = tfidfnorm.TfIdfnorm()
         norm_okapi = okapi.Okapi(average_words)
	 norm_power = powerNorm.PowerNorm()
      
         names_normalization = np.array(["SBIN","TFNORM","TFIDF","TFIDF2","TFIDFNORM", "OKAPI", "POWER"])
         normalization_method = np.array([norm_sbin,norm_tfnorm,norm_tfidf,norm_tfidf2, norm_tfidfnorm, norm_okapi,norm_power])
         
         #Get the detector passed in the -h argument
         index = np.where(names_normalization==histnorm)[0]
         if index.size > 0:
            normalization_to_use = normalization_method[index[0]]
            new_hist = normalization_to_use.normalizeHist(hist, new_size, n_images)
         else:
            print 'Wrong normalization name passed in the -h argument. Options: SBIN, TFNORM, TFIDF and TFIDF2'
            sys.exit()     
         
         #FOR RESULTS FILE
         normalization_to_use.writeFile(f)      
            
      else:
         #FOR RESULTS FILE
         f.write("No histogram normalization applied\n")
         new_hist = hist
      
      #################################################################
      #
      # Clustering of the features
      #
      #################################################################     
      
      #save current time
      start_time = time.time()     
   
      #Get detector classes
      clust_dbscan = Dbscan.Dbscan(dist)
      clust_kmeans = KMeans1.KMeans1([nclusters])
      clust_birch = Birch.Birch(nclusters)
      clust_meanSift = meanSift.MeanSift(nclusters)
      clust_hierar1 = hierarchicalClustering.Hierarchical(nclusters, dist)
      clust_hierar2 = hierarchicalClustScipy.HierarchicalScipy(dist)
      clust_community = communityDetection.CommunityDetection(dist)
      
      names_clustering = np.array(["DBSCAN", "KMEANS", "BIRCH", "MEANSIFT", "HIERAR1", "HIERAR2","COMM"])
      clustering_algorithm = np.array([clust_dbscan, clust_kmeans, clust_birch, clust_meanSift, clust_hierar1, clust_hierar2,clust_community])
      
      #Get the detector passed in the -a argument
      index = np.where(names_clustering==clust)[0]
      if index.size > 0:
         clustering_to_use = clustering_algorithm[index[0]]
      else:
         print 'Wrong clustering algorithm name passed in the -a argument. Options: DBSCAN, KMEANS, BIRCH, MEANSIFT, HIERAR1, HIERAR2, COMM'
         sys.exit()      
         
      clusters = clustering_to_use.obtainClusters(new_hist)   
      
      #FOR RESULTS FILE
      clustering_to_use.writeFileCluster(f)
      
      elapsed_time = (time.time() - start_time)
      print 'Time to run clustering algorithm = ' + str(elapsed_time) 
      f.write('Time to run clustering algorithm = ' + str(elapsed_time) + '\n')
      
      print 'Number of clusters obtained = ' + str(max(clusters)+1)
      f.write('Number of clusters obtained = ' + str(max(clusters)+1) + '\n')
      
      nclusters = max(clusters)+1
      
      print 'Clusters obtained = ' + str(np.asarray(clusters))
      
      #date_time = datetime.datetime.now().strftime('%b-%d-%I%M%p-%G')
      #np.savetxt('saveClusters_'+date_time+'_.txt', clusters, '%i', ',')
      
      #ADDED
      #################################################################
      #
      # Create folder with central images for each cluster
      #
      #################################################################  
      
      #obtain representative images for each cluster
      central_ims = clust_community.obtainCenteralImages(new_hist, clusters)      
      
      central_folder = os.path.join(dir_results,'CenterImages')
      if not os.path.exists(central_folder):
	 os.makedirs(central_folder)    
      
      count=0
      for central_im in central_ims:
	 filename = os.path.join(central_folder,'Cluster_'+str(count)+'.jpg')
	 img = cv2.imread(imPaths[central_im],1)
	 cv2.imwrite(filename, img) 	    
	 count = count + 1
      
      #ADDED
      #################################################################
      #
      # Separate Clusters into folders
      #
      #################################################################     
   
      clusters_folder = os.path.join(dir_results,'Clusters')
      if not os.path.exists(clusters_folder):
	 os.makedirs(clusters_folder) 
	 
      clust_dir = []
      for iclust in range(0,nclusters):
	 direc = os.path.join(clusters_folder,'Cluster_'+str(iclust))
	 if not os.path.exists(direc):
	    os.makedirs(direc)	 
	 clust_dir.append(direc)
      
      for im in range(0,len(imPaths)):
	 im_name = imPaths[im].split('/')[-1]
	 #print clust_dir[int(clusters[im])]
	 filename = os.path.join(clust_dir[int(clusters[im])],im_name)
	 #print filename
	 img = cv2.imread(imPaths[im],1)
	 cv2.imwrite(filename, img) 	
	 
      #################################################################
      #
      # Evaluation
      #
      #################################################################  
      
      users = 0
      
      if users == 1:
	 
	 rand_index = evaluationUsers.randIndex(clusters)
	 rand_indexes.append(rand_index)
	 print 'rand_index = ' + str(rand_index)
	 f.write("Rand Index = " + str(rand_index) + "\n")	 
	 
      else:
	 if len(clusters) == len(labels):
   
	    f.write("\nResults\n")
   
	    f.write('Clusters Obtained = ' + str(np.asarray(clusters)))
	    f.write('Labels = ' + str(np.asarray(labels)))
	     
	    rand_index = metrics.adjusted_rand_score(labels, clusters)
	    rand_indexes.append(rand_index)
	    print 'rand_index = ' + str(rand_index)
	    f.write("Rand Index = " + str(rand_index) + "\n")
		 
	    NMI_index = metrics.normalized_mutual_info_score(labels, clusters)
	    nmi_indexes.append(NMI_index)
	    print 'NMI_index = ' + str(NMI_index)   
	    f.write("NMI Index = " + str(NMI_index) + "\n")
   
   if rep > 1:
      f.write("\nFINAL RESULTS\n")
      f.write("Avg Rand Index = " + str(float(sum(rand_indexes))/rep) + "\n")
      f.write("Std Rand Index = " + str(statistics.stdev(rand_indexes)) + "\n")
      if users != 1:
	 f.write("Avg NMI Index = " + str(float(sum(nmi_indexes))/rep) + "\n")
	 f.write("Std NMI Index = " + str(statistics.stdev(nmi_indexes)) + "\n")
   f.close()
