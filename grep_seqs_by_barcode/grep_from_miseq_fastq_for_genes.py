#-*-coding:utf-8-*-
'''
Author:	Liu wei
Data:	2015.01.15
Usage:	python grep_from_miseq_fastq_20150115.py  input_seqs_ul.fastq  mapping.txt edit_output.fastq
		edit_output.fastq : 找到从反向引物端开始测序的reads，且以对应的正向引物的反向互补序列结束的reads，然后进行反向互补
		mapping.txt like this:
		#SampleID       BarcodeSequence LinkerPrimerSequence    ReversePrimer   Description
		ND1     TCCCTTGTCTCC    GTGCCAGCMGCCGCGGTAA     GGACTACHVGGGTWTCTAAT    806rcbc0
		ND2     ACGAGACTGATT    GTGCCAGCMGCCGCGGTAA     GGACTACHVGGGTWTCTAAT    806rcbc1
'''
#need cogent/ and fastq.py
import os,sys,re,argparse
from fastq import MinimalFastqParser
			
#return a array like this:[['V3-6F', 'ATATGCTGCCTACGGGAGGCAGCAG'], ['V3-7F', 'ATAGCATGCCTACGGGAGGCAGCAG']]
def primer_list( ul ):
	f = open( ul )
	lines = f.readlines()
	primers = []
	for line in lines[1:]:
		temp = line.split( '\t' )
		primer = []
		primer.append( temp[0].strip() ) #sample id
		primer.append( temp[1].strip()+temp[2].strip() ) #barcode+forwrad primer
		primer.append( temp[3].strip() ) #reverse primer
		primers.append( primer )
	f.close()
	return primers

#Reverse complementary sequence
def reverse_com_seq( seq ):
	new_seq = ''.join(["ATCGNFXRYMKSWHBVD"["TAGCNFXRYMKSWHBVD".index(n)] for n in seq[::-1]])
	return new_seq

#reverse a sequence
def reverse_seq( seq ):
	new_seq = seq[::-1]
	return new_seq
	
#change primers that containing Jianbing base. GGACTACCVGGGTATCTAAT to rc ATTAGATACCC[CTG]GGTAGTCC
def change_primer_seqs( primer ):
	#jianbing_base_dic = {'R':'[AG]','Y':'[CT]','M':'[AC]','K':'[GT]','S':'[GC]','W':'[AT]','H':'[ATC]','B':'[GTC]','V':'[GAC]','D':'[GAT]','N':'[AGCT]'}
	jianbing_base_dic = {'R':'[CT]','Y':'[AG]','M':'[GT]','K':'[AC]','S':'[GC]','W':'[TA]','H':'[GAT]','B':'[GAC]','V':'[GTC]','D':'[ATC]','N':'[AGCT]'}
	base_list = []
	rc_primer = reverse_com_seq( primer )
	for base in rc_primer:
		if base in jianbing_base_dic.keys():
			new_base = jianbing_base_dic[base]
			base_list.append( new_base )
		else:
			base_list.append( base )
	new_primer_seq = ''.join( base_list )
	return new_primer_seq
	
def usage():
    print """
		Usage:   python grep_from_miseq_fastq_20150115.py  input_seqs_ul.fastq  mapping.txt ouput_dir
		This script modified at 20150115, used for the new Hiseq Platform 2x250bp, for at the end of every seqs 2 extra base like TA or TG are added.
		mapping.txt like this, barcode and reverse primer all NEEDED!!!:
		#SampleID       BarcodeSequence LinkerPrimerSequence    ReversePrimer   Description
		ND1     TCCCTTGTCTCC    GTGCCAGCMGCCGCGGTAA     GGACTACHVGGGTWTCTAAT    806rcbc0
		ND2     ACGAGACTGATT    GTGCCAGCMGCCGCGGTAA     GGACTACHVGGGTWTCTAAT    806rcbc1
		"""

def __main__():
	try:
		input_seqs_ul = sys.argv[1]
		primer_ul = sys.argv[2]
		output_dir = sys.argv[3]
	except:
		usage()
		sys.exit(1)
	
	primers = primer_list( primer_ul )
	output_fq =  output_dir + '/greped.fq'
	outf = open( output_fq , 'w')
	grep_seqs_log = output_dir + '/grep_seqs_num_log.txt'
	grep_log = open( grep_seqs_log, 'w' )
	
	#initiate an empty dic to record the greped seqs numbers.
	grep_seqs_dic = {}
	for primer in primers:
		grep_seqs_dic[ primer[0] ] = 0
	
	#no_matched_seqs = 0
	matched_seqs = 0
	total_seqs_num = 0
	
	#pattern = re.compile( 'ATTAGATACCC[CTG]GGTAGTCC' )#reverse primer is GGACTACCVGGGTATCTAAT containing JianBing bases,rc is ATTAGATACCC[CTG]GGTAGTCC.
	rprimer = primers[0][2]
	rprimer_len = len( rprimer )
	rc_rprimer = change_primer_seqs( rprimer )
	pattern = re.compile( rc_rprimer )
	
	for seq_id, seq, qual  in MinimalFastqParser(input_seqs_ul, strict=False):
		total_seqs_num = total_seqs_num + 1
		for primer in primers:
			if seq.startswith( primer[1] ):
				try:
					new_seq = pattern.split( seq )[0] #remove reverse primer
					outf.write('@%s\n%s\n+\n%s\n' % (seq_id, new_seq, qual))
					grep_seqs_dic[ primer[0] ] = grep_seqs_dic[ primer[0] ] + 1
					matched_seqs = matched_seqs + 1
					break
				except:
					outf.write('@%s\n%s\n+\n%s\n' % (seq_id, seq, qual))
					grep_seqs_dic[ primer[0] ] = grep_seqs_dic[ primer[0] ] + 1
					matched_seqs = matched_seqs + 1
					break
			elif reverse_com_seq(primer[1]) in seq[-40:]:
				fpart_seq = seq[rprimer_len:-40]
				rpart_seq = seq[-40:]
				new_rpart = rpart_seq[ :rpart_seq.index(reverse_com_seq(primer[1])) ]
				new_seq = primer[1] + reverse_com_seq( fpart_seq + new_rpart )
				#new_qual = qual[ :seq.index( reverse_com_seq(primer[1]) ) + len(primer[1]) ]
				new_qual = qual[:len(new_seq)]
				outf.write('@%s\n%s\n+\n%s\n' % (seq_id+'|reverse', new_seq, new_qual))
				grep_seqs_dic[ primer[0] ] = grep_seqs_dic[ primer[0] ] + 1
				matched_seqs = matched_seqs + 1
				break
			#else:
				#no_matched_seqs = no_matched_seqs + 1
				#break

	grep_log.write( "There are %s seqs totally!\n" % total_seqs_num )
	grep_log.write( "Matched seqs: %s !\n" % matched_seqs )
	grep_log.write( "No matched seqs: %s !\n" % (total_seqs_num-matched_seqs) )
	grep_log.write( "Reverse primer is: %s !\n" % rprimer )
	grep_log.write( "RC. reverse primer is: %s !\n" % rc_rprimer )
	
	lib_name = os.path.basename(input_seqs_ul).split('.')[0]
	for key in grep_seqs_dic:
		grep_log.write( '%s\t%s\t%s\n' % (key, grep_seqs_dic[key], lib_name) )
	grep_log.close()
	outf.close()

if __name__ == "__main__" : __main__()