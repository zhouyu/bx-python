#!/usr/bin/python2.4
import sys
from bx.bitset import *
from bx.bitset_builders import *

"""
Readers for bed/gtf/gff formats 

GeneReader: yields exons
CDSReader: yields cds_exons
FeatureReader: yields cds_exons,introns, exons

For gff/gtf, the start_codon stop_codon line types are merged with CDSs.

"""

def GeneReader( fh, format='gff' ):
    """ yield chrom, strand, gene_exons, name """

    known_formats = ( 'gff', 'gtf', 'bed')
    if format not in known_formats: 
        print >>sys.stderr,  '%s format not in %s' % (format, ",".join( known_formats ))
        raise '?'
    
    if format == 'bed':
        for line in fh:    
            f = line.strip().split()
            chrom = f[0]
            chrom_start = int(f[1])
            name = f[4]
            strand = f[5]
            cdsStart = int(f[6])
            cdsEnd = int(f[7])
            blockCount = int(f[9])
            blockSizes = [ int(i) for i in f[10].strip(',').split(',') ]
            blockStarts = [ chrom_start + int(i) for i in f[11].strip(',').split(',') ]

            # grab cdsStart - cdsEnd
            gene_exons = []
            for base,offset in zip( blockStarts, blockSizes ):
                exon_start = base
                exon_end = base+offset
                gene_exons.append( (exon_start, exon_end) )
            yield chrom, strand, gene_exons, name
    genelist = {}
    grouplist = []
    if format == 'gff' or format == 'gtf':
        for line in fh:
            if line.startswith('#'): continue
            fields = line.strip().split('\t')
            if len( fields ) < 9: continue

            # fields

            chrom = fields[0]
            ex_st = int( fields[3] ) - 1 # make zero-centered
            ex_end = int( fields[4] ) #+ 1 # make exclusive
            strand = fields[6]

            if format == 'gtf':
                group = fields[8].split(';')[0]
            else:
                group = fields[8]

            if group not in grouplist: grouplist.append( group )
            if group not in genelist:
                genelist[group] = (chrom, strand, [])
            exons_i = 2
            genelist[group][exons_i].append( ( ex_st, ex_end ) )

        sp = lambda a,b: cmp( a[0], b[0] )

        #for gene in genelist.values():
        for gene in grouplist:
            chrom, strand, gene_exons = genelist[ gene ]
            gene_exons = bitset_union( gene_exons )
            yield chrom, strand, gene_exons, gene

def CDSReader( fh, format='gff' ):
    """ yield chrom, strand, cds_exons, name """

    known_formats = ( 'gff', 'gtf', 'bed')
    if format not in known_formats: 
        print >>sys.stderr,  '%s format not in %s' % (format, ",".join( known_formats ))
        raise '?'
    
    if format == 'bed':
        for line in fh:    
            f = line.strip().split()
            chrom = f[0]
            chrom_start = int(f[1])
            name = f[4]
            strand = f[5]
            cdsStart = int(f[6])
            cdsEnd = int(f[7])
            blockCount = int(f[9])
            blockSizes = [ int(i) for i in f[10].strip(',').split(',') ]
            blockStarts = [ chrom_start + int(i) for i in f[11].strip(',').split(',') ]

            # grab cdsStart - cdsEnd
            cds_exons = []
            cds_seq = ''
            genome_seq_index = []
            for base,offset in zip( blockStarts, blockSizes ):
                if (base + offset) < cdsStart: continue
                if base > cdsEnd: continue
                exon_start = max( base, cdsStart )
                exon_end = min( base+offset, cdsEnd ) 
                cds_exons.append( (exon_start, exon_end) )
            yield chrom, strand, cds_exons, name

    genelist = {}
    grouplist = []
    if format == 'gff' or format == 'gtf':
        for line in fh:
            if line.startswith('#'): continue
            fields = line.strip().split('\t')
            if len( fields ) < 9: continue
            if fields[2] not in ('CDS', 'stop_codon', 'start_codon'): continue

            # fields

            chrom = fields[0]
            ex_st = int( fields[3] ) - 1 # make zero-centered
            ex_end = int( fields[4] ) #+ 1 # make exclusive
            strand = fields[6]

            if format == 'gtf':
                group = fields[8].split(';')[0]
            else:
                group = fields[8]

            if group not in grouplist: grouplist.append( group )
            if group not in genelist:
                genelist[group] = (chrom, strand, [])
            
            genelist[group][2].append( ( ex_st, ex_end ) )

        sp = lambda a,b: cmp( a[0], b[0] )

        #for gene in genelist.values():
        for gene in grouplist:
            chrom, strand, cds_exons = genelist[ gene ]
            seqlen = sum([ a[1]-a[0] for a in cds_exons ])
            overhang = seqlen % 3
            if overhang > 0:
                #print >>sys.stderr, "adjusting ", gene  
                if strand == '+': 
                    cds_exons[-1] = ( cds_exons[-1][0], cds_exons[-1][1] - overhang )
                else:
                    cds_exons[0] = ( cds_exons[0][0] + overhang, cds_exons[0][1] )
            cds_exons = bitset_union( cds_exons )
            yield chrom, strand, cds_exons, gene

def FeatureReader( fh, format='gff', alt_introns_subtract="exons", gtf_parse=None):
    """ 
    yield chrom, strand, cds_exons, introns, exons, name

    gtf_parse Example:
    # parse gene_id from transcript_id "AC073130.2-001"; gene_id "TES";
    gene_name = lambda s: s.split(';')[1].split()[1].strip('"')

    for chrom, strand, cds_exons, introns, exons, name in FeatureReader( sys.stdin, format='gtf', gtf_parse=gene_name )
    """

    known_formats = ( 'gff', 'gtf', 'bed')
    if format not in known_formats: 
        print >>sys.stderr,  '%s format not in %s' % (format, ",".join( known_formats ))
        raise '?'
    
    if format == 'bed':
        for line in fh:    
            f = line.strip().split()
            chrom = f[0]
            chrom_start = int(f[1])
            name = f[4]
            strand = f[5]
            cdsStart = int(f[6])
            cdsEnd = int(f[7])
            blockCount = int(f[9])
            blockSizes = [ int(i) for i in f[10].strip(',').split(',') ]
            blockStarts = [ chrom_start + int(i) for i in f[11].strip(',').split(',') ]

            # grab cdsStart - cdsEnd
            cds_exons = []
            exons = []
            
            cds_seq = ''
            genome_seq_index = []
            for base,offset in zip( blockStarts, blockSizes ):
                if (base + offset) < cdsStart: continue
                if base > cdsEnd: continue
                # exons
                exon_start = base
                exon_end = base+offset
                exons.append( (exon_start, exon_end) )
                # cds exons
                exon_start = max( base, cdsStart )
                exon_end = min( base+offset, cdsEnd ) 
                cds_exons.append( (exon_start, exon_end) )
            cds_exons = bitset_union( cds_exons )
            exons = bitset_union( exons )
            introns = bitset_complement( exons )
            yield chrom, strand, cds_exons, introns, exons, name

    genelist = {}
    grouplist = []
    if format == 'gff' or format == 'gtf':
        for line in fh:
            if line.startswith('#'): continue
            fields = line.strip().split('\t')
            if len( fields ) < 9: continue

            # fields

            chrom = fields[0]
            ex_st = int( fields[3] ) - 1 # make zero-centered
            ex_end = int( fields[4] ) #+ 1 # make exclusive
            strand = fields[6]

            if format == 'gtf':
                if not gtf_parse:
                    group = fields[8].split(';')[0]
                else:
                    group = gtf_parse( fields[8] )
            else:
                group = fields[8]

            if group not in grouplist: grouplist.append( group )
            if group not in genelist:
                # chrom, strand, cds_exons, introns, exons
                genelist[group] = (chrom, strand, [], [], [])
            
            if fields[2] == 'exon':
                genelist[group][4].append( ( ex_st, ex_end ) )
            elif fields[2] in ('CDS', 'stop_codon', 'start_codon'):
                genelist[group][2].append( ( ex_st, ex_end ) )
            elif fields[2] == 'intron':
                genelist[group][3].append( ( ex_st, ex_end ) )

        sp = lambda a,b: cmp( a[0], b[0] )

        #for gene in genelist.values():
        for gene in grouplist:
            chrom, strand, cds_exons, introns, exons = genelist[ gene ]
            seqlen = sum([ a[1]-a[0] for a in cds_exons ])
            overhang = seqlen % 3
            if overhang > 0:
                #print >>sys.stderr, "adjusting ", gene  
                if strand == '+': 
                    cds_exons[-1] = ( cds_exons[-1][0], cds_exons[-1][1] - overhang )
                else:
                    cds_exons[0] = ( cds_exons[0][0] + overhang, cds_exons[0][1] )

            cds_exons = bitset_union( cds_exons )
            exons = bitset_union( exons )

            if alt_introns_subtract:
                if alt_introns_subtract == 'exons':
                    introns = bitset_subtract( introns, exons )
                if alt_introns_subtract == 'cds_exons':
                    introns = bitset_subtract( introns, cds_exons )
            else:
                introns = bitset_union( introns )

            yield chrom, strand, cds_exons, introns, exons, gene

def bitset_subtract( ex1, ex2 ):
    bits1 = BinnedBitSet(MAX)
    for l in ex1:
        start, end = l[0], l[1]
        bits1.set_range( start, end - start )
    bits2 = BinnedBitSet(MAX)
    for l in ex1:
        start, end = l[0], l[1]
        bits2.set_range( start, end - start )

    bits2.invert()
    bits1.iand( bits2 )
    return bits2list( bits1 )

def bits2list( bits ):
    ex = []
    end = 0
    while 1:
        start = bits.next_set( end )
        if start == bits.size: break
        end = bits.next_clear( start )
        ex.append( (start, end) )

    return ex

def bitset_complement( exons ):
    bits = BinnedBitSet(MAX)
    introns = []
    for l in exons:
        start, end = l[0], l[1]
        bits.set_range( start, end - start )
    bits.invert()

    # only complement within the range of the list
    ex_start = min( [a[0] for a in exons] )
    ex_end = max( [a[1] for a in exons] )
    end = ex_start
    len = ex_end
    while 1:
            start = bits.next_set( end )
            if start == bits.size: break
            end = bits.next_clear( start )
            if end > len: end = len
            if start != end:
                introns.append( (start,end ) )
            if end == len: break
    return introns 


def bitset_union( exons ):
    bits = BinnedBitSet(MAX)
    Uexons = []
    for l in exons:
        start, end = l[0], l[1]
        bits.set_range( start, end - start )
    end = 0
    while 1:
        start = bits.next_set( end )
        if start == bits.size: break
        end = bits.next_clear( start )
        Uexons.append( (start, end) )

    return Uexons