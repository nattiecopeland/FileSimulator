#!/usr/bin/env python3
import sys
from collections import OrderedDict

numPages = 256
numTLBEntries = 16
pageSize = 256
frameSize = 256
blockSize = 256

offsetBits = 8
offsetMask = 255
pageMask = 255

tlb = OrderedDict()

pageTable = []

numFrames = 256

refList = []
backStore = []

mainMem = []

def evict(page, victimF):
   #print('used fifo')
   #"remove" the victim from main memory
   victimPage = pageTable.index([victimF, 1])
   pageTable[victimPage][1] = 0
   #remove the victims tlb entry
   tlb.pop(victimPage)
   #update the page table entry of the current page
   pageTable[page][0] = victimF
   pageTable[page][1] = 1
   mainMem[victimF] = backStore[page]
   #add page to the tlb (will be done in main)
   #tlb[page] = victimF
   return victimF

def lru(page, refI):
   currI = refI - 1
   #populate a 'check list' with every frame index
   checkList = []
   for i in range(numFrames):
      checkList.append(i)
   #go back through reference sheet and remove referenced frame indexes until one remains
   while currI >= 0 and len(checkList) > 1:
      currFrame = pageTable[(refList[currI] >> offsetBits) & pageMask][0]
      if currFrame in checkList:
         checkList.remove(currFrame)
      currI -= 1
   #evict and replace lest recently referenced frame
   victimF = checkList[0]
   return evict(page, victimF)

def opt(page, refI):
   currI = refI + 1
   #populate a 'check list' with every frame index
   checkList = []
   for i in range(numFrames):
      checkList.append(i)
   #go back through reference sheet and remove referenced frame indexes until one remains
   while currI < len(refList) and len(checkList) > 1:
      currFrame = pageTable[(refList[currI] >> offsetBits) & pageMask]
      if currFrame[1] == 1 and currFrame[0] in checkList:
         checkList.remove(currFrame[0])
      currI += 1
   #evict and replace lest recently referenced frame
   victimF = checkList[0]
   return evict(page, victimF)

def main(argv):
   if len(argv) < 2 or len(argv) > 4:
      print("Usage: memSim <reference-sequence-file.txt> <FRAMES> <PRA>")
      exit(1)

   pageFaults = 0
   tlbHits = 0
   currFrames = 0
   currNumTLBEntries = 0
   victimI = 0
   pra = 0

   #outFile = open('output.txt', 'w')

   #initialize pageTable
   for i in range(numPages):
      pageTable.append([-1, 0])

   #reference sequence of logical addresses
   refSeq = argv[1]
   #check arguments
   for i in range(2, len(argv)):
      if argv[i] in ('LRU', 'lru'):
         pra = 1
      elif argv[i] in ('OPT', 'opt'):
         pra = 2
      else:
         try:
            num = int(argv[i])
         except:
            continue
         else:
            if int(argv[i]) > 0 and int(argv[i]) <= numPages:
               global numFrames
               numFrames = int(argv[i])

   #collect the referenced adresses into a list
   file = open(refSeq, 'r')
   lines = file.readlines()
   for line in lines:
      chars = line.rstrip()
      refList.append(int(chars))
   file.close()

   #populate the backStore
   with open("BACKING_STORE.bin", "rb") as in_file:
      while True:
         piece = in_file.read(blockSize)
         if len(piece) == 0:
            break # end of file
         backStore.append(piece)

   #create mainMem with bogus values
   #mainMem = backStore[:numFrames]
   for i in range(numFrames):
      mainMem.append(backStore[i])

   #for LRU
   refI = 0

   #go through each address reference
   for virt in refList:
      offset = virt & offsetMask
      page = (virt >> offsetBits) & pageMask
      #check tlb
      real = tlb.get(page)
      if real != None:
         #tlb hit
         tlbHits += 1
         tlb.pop(page)
         tlb[page] = real
      else:
         #tlb miss
         if pageTable[page][1] == 0:
            #page fault
            pageFaults += 1
            if currFrames < numFrames:
               #open frame
               pageTable[page][0] = currFrames
               pageTable[page][1] = 1
               real = currFrames
               mainMem[real] = backStore[page]
               currFrames+=1
            else:
               #full RAM, use PRA
               if pra == 1:
                  #LRU
                  real = lru(page, refI)
               elif pra == 2:
                  #OPT
                  real = opt(page, refI)
               else:
                  #FIFO
                  real = evict(page, victimI)
                  victimI = (victimI + 1)%numFrames
               #evict removes victim tlb entry but does not add new entry
               currNumTLBEntries-=1
         else:
            real = pageTable[page][0]
         #update tlb
         if currNumTLBEntries == numTLBEntries:
            #tlb is full
            tlb.popitem(last = False)
         else:
            currNumTLBEntries += 1
         tlb[page] = real
         
      #two's compliment (make byte accessed signed)
      num = mainMem[real][offset]
      if num > 127:
         num -= 256
      #print out reference data
      print('%d, %d, %d, %s\n' % (virt, num, real, mainMem[real].hex()))
      refI+=1

   #print agregate data
   print('Number of Translated Addresses = %d\n' % len(refList))
   print('Page Faults = %d\n' % pageFaults)
   print('Page Fault Rate = %.3f\n' % (float(pageFaults) / len(refList)))
   print('TLB Hits = %d\n' % tlbHits)
   print('TLB Misses = %d\n' % (len(refList) - tlbHits))
   print('TLB Hit Rate = %.3f\n' % (float(tlbHits) / len(refList)))
   #outFile.close()

if __name__ == "__main__":
   main(sys.argv)