"""
genomic_tools.py — SenGenoScope v5
VEP corrigé: URL GET avec polyphen=b&sift=b&cadd=1&hgvs=1&canonical=1
Source: https://rest.ensembl.org/documentation/info/vep_region_get
"""

import re, requests

CODON_TABLE = {
    'TTT':'Phe','TTC':'Phe','TTA':'Leu','TTG':'Leu','CTT':'Leu','CTC':'Leu','CTA':'Leu','CTG':'Leu',
    'ATT':'Ile','ATC':'Ile','ATA':'Ile','ATG':'Met','GTT':'Val','GTC':'Val','GTA':'Val','GTG':'Val',
    'TCT':'Ser','TCC':'Ser','TCA':'Ser','TCG':'Ser','CCT':'Pro','CCC':'Pro','CCA':'Pro','CCG':'Pro',
    'ACT':'Thr','ACC':'Thr','ACA':'Thr','ACG':'Thr','GCT':'Ala','GCC':'Ala','GCA':'Ala','GCG':'Ala',
    'TAT':'Tyr','TAC':'Tyr','TAA':'Stop','TAG':'Stop','CAT':'His','CAC':'His','CAA':'Gln','CAG':'Gln',
    'AAT':'Asn','AAC':'Asn','AAA':'Lys','AAG':'Lys','GAT':'Asp','GAC':'Asp','GAA':'Glu','GAG':'Glu',
    'TGT':'Cys','TGC':'Cys','TGA':'Stop','TGG':'Trp','CGT':'Arg','CGC':'Arg','CGA':'Arg','CGG':'Arg',
    'AGT':'Ser','AGC':'Ser','AGA':'Arg','AGG':'Arg','GGT':'Gly','GGC':'Gly','GGA':'Gly','GGG':'Gly',
}
COMPLEMENT = str.maketrans('ATCGatcg','TAGCtagc')


def parse_fasta(text):
    text = text.strip()
    if text.startswith('>'):
        lines = text.split('\n'); header = lines[0][1:].strip()
        seq = ''.join(l.strip() for l in lines[1:] if not l.startswith('>'))
    else:
        header = "Séquence soumise"; seq = ''.join(text.split())
    return {"header": header, "sequence": re.sub(r'[^ATCGNatcgn]','',seq).upper()}


def analyze_sequence(seq):
    n = len(seq)
    if n == 0: return {"error":"Séquence vide"}
    a,t,c,g,nc = seq.count('A'),seq.count('T'),seq.count('C'),seq.count('G'),seq.count('N')
    gc = round((g+c)/max(n-nc,1)*100,2)
    return {
        "length":n,"gc_content":gc,"composition":{"A":a,"T":t,"C":c,"G":g,"N":nc},
        "gc_interpretation":interpret_gc(gc),
        "reverse_complement":(seq[::-1].translate(COMPLEMENT))[:80]+"...",
        "protein_frame1":translate_sequence(seq)[:60],
        "premature_stops":detect_premature_stops(seq),
        "simple_repeats":find_simple_repeats(seq)[:5],
        "restriction_sites":find_restriction_sites(seq),
        "cpg_sites":seq.count('CG'),
        "cpg_ratio_per_kb":round(seq.count('CG')/max(n,1)*1000,2),
        "cpg_island_candidate":seq.count('CG')/max(n,1)*1000>6 and gc>50,
    }


def translate_sequence(seq):
    p=[]
    for i in range(0,len(seq)-2,3):
        aa=CODON_TABLE.get(seq[i:i+3],'?')
        if aa=='Stop': p.append('*'); break
        p.append(aa[:1])
    return '-'.join(p)


def detect_premature_stops(seq):
    stops=[]
    for f in range(3):
        for i in range(f,len(seq)-2,3):
            if CODON_TABLE.get(seq[i:i+3])=='Stop':
                stops.append({"frame":f"+{f+1}","position":i+1,"codon":seq[i:i+3]})
    return stops[:10]


def find_simple_repeats(seq):
    found=[]
    for ul in [2,3,4]:
        for i in range(len(seq)-ul*3):
            u=seq[i:i+ul]
            if len(set(u))==1: continue
            c=1
            while i+ul*(c+1)<=len(seq) and seq[i+ul*c:i+ul*(c+1)]==u: c+=1
            if c>=4: found.append({"unit":u,"count":c,"position":i+1,"total_length":ul*c})
    return sorted(found,key=lambda x:-x['count'])


def find_restriction_sites(seq):
    enz={'EcoRI':'GAATTC','BamHI':'GGATCC','HindIII':'AAGCTT','NotI':'GCGGCCGC','XhoI':'CTCGAG','NcoI':'CCATGG','XbaI':'TCTAGA','SalI':'GTCGAC','KpnI':'GGTACC','SmaI':'CCCGGG'}
    return [{"enzyme":n,"site":s,"positions":[m.start()+1 for m in re.finditer(s,seq)],"count":len(re.findall(s,seq))} for n,s in enz.items() if re.search(s,seq)]


def interpret_gc(gc):
    if gc<35: return "GC très faible — région AT-riche, instabilité potentielle"
    if gc<45: return "GC faible — région normale"
    if gc<=60: return "GC normal — typique du génome humain"
    if gc<=70: return "GC élevé — possible îlot CpG ou promoteur actif"
    return "GC très élevé — probable îlot CpG, région régulatrice"


def compare_sequences(seq1,seq2):
    if len(seq1)!=len(seq2): return {"error":f"Longueurs différentes ({len(seq1)} vs {len(seq2)})"}
    muts=[]
    for i,(b1,b2) in enumerate(zip(seq1,seq2)):
        if b1!=b2:
            t='Transition' if (b1,b2) in {('A','G'),('G','A'),('C','T'),('T','C')} else 'Transversion'
            muts.append({"position":i+1,"ref":b1,"alt":b2,"type":t,"notation":f"c.{i+1}{b1}>{b2}"})
    ts=sum(1 for m in muts if m['type']=='Transition'); tv=len(muts)-ts
    return {"total_mutations":len(muts),"identity_percent":round((len(seq1)-len(muts))/len(seq1)*100,2),"mutations":muts[:20],"transitions":ts,"transversions":tv,"ts_tv_ratio":round(ts/max(tv,1),2),"mutation_density":round(len(muts)/len(seq1)*1000,2)}


# ══ VEP CORRIGÉ ══════════════════════════════════════════════════════════════
# Source: https://rest.ensembl.org/documentation/info/vep_region_get
# URL GET: /vep/human/region/{chr}:{pos}-{pos}/{allele}?polyphen=b&sift=b&cadd=1&hgvs=1&canonical=1
# Refs: McLaren 2016 (PMID 27268795), Adzhubei 2010 (PMID 20354512),
#        Kumar 2009 (PMID 19561590), Kircher 2014 (PMID 24487276)

def predict_variant_impact(chrom, pos, ref, alt, assembly="GRCh38"):
    chrom = str(chrom).replace("chr","").strip()
    server = "https://grch37.rest.ensembl.org" if assembly=="GRCh37" else "https://rest.ensembl.org"
    hdrs = {"Content-Type":"application/json","Accept":"application/json"}

    # URL GET correcte — paramètres obligatoires pour obtenir PolyPhen/SIFT/CADD
    url = (f"{server}/vep/human/region/{chrom}:{pos}-{pos}:1/{alt}"
           f"?content-type=application/json&polyphen=b&sift=b&cadd=1&hgvs=1&canonical=1&numbers=1")

    try:
        r = requests.get(url, headers=hdrs, timeout=25)

        # Fallback POST si GET échoue
        if r.status_code not in (200,201):
            r = requests.post(f"{server}/vep/human/region", headers=hdrs, timeout=25,
                json={"variants":[f"{chrom} {pos} . {ref} {alt} . . ."],
                      "polyphen":"b","sift":"b","cadd":True,"hgvs":True,"canonical":True,"numbers":True})
            if r.status_code not in (200,201):
                return {"error":f"Ensembl VEP {r.status_code}. Vérifiez: chr sans 'chr' (ex: 17), position GRCh38/37, ref/alt en majuscules.","api_url":url}

        results = r.json()
        if not results or not isinstance(results,list):
            return {"error":"Aucun résultat VEP — variant introuvable dans Ensembl."}

        res = results[0]
        cons = res.get("transcript_consequences",[])

        if not cons:
            return {"variant":f"{chrom}:{pos} {ref}>{alt}","consequence":["intergenic_variant"],"impact":"MODIFIER",
                    "hgvsc":"","hgvsp":"","gene_symbol":"Intergénique","transcript_id":"",
                    "polyphen_score":None,"polyphen_prediction":"N/A","polyphen_interpretation":"Non applicable (intergénique)",
                    "sift_score":None,"sift_prediction":"N/A","sift_interpretation":"Non applicable (intergénique)",
                    "cadd_raw":None,"cadd_phred":None,"cadd_interpretation":"Non calculé",
                    "overall_pathogenicity":{"score":0,"max":7,"category":"Non évaluable","factors":[]},"all_transcripts":[],"api_url":url}

        # Prioriser: canonique > impact élevé
        rank={"HIGH":0,"MODERATE":1,"LOW":2,"MODIFIER":3}
        cons_sorted=sorted(cons,key=lambda c:(0 if c.get("canonical") else 1,rank.get(c.get("impact","MODIFIER"),3)))
        c=cons_sorted[0]

        # Scores — directement dans transcript_consequences (correct avec polyphen=b&sift=b)
        pp=c.get("polyphen_score"); pp_pred=c.get("polyphen_prediction","")
        sift=c.get("sift_score"); sift_pred=c.get("sift_prediction","")

        # CADD — niveau variant ou transcript
        cadd_p=res.get("cadd_phred") or c.get("cadd_phred")
        cadd_r=res.get("cadd_raw") or c.get("cadd_raw")
        if cadd_p is None:
            for cv in res.get("colocated_variants",[]):
                if cv.get("cadd_phred") is not None:
                    cadd_p=cv["cadd_phred"]; cadd_r=cv.get("cadd_raw"); break

        all_t=[{
            "transcript":x.get("transcript_id",""),"gene":x.get("gene_symbol",x.get("gene_id","")),"biotype":x.get("biotype",""),
            "consequence":x.get("consequence_terms",[]),"impact":x.get("impact",""),
            "hgvsc":x.get("hgvsc",""),"hgvsp":x.get("hgvsp",""),
            "polyphen":x.get("polyphen_score"),"sift":x.get("sift_score"),"canonical":bool(x.get("canonical"))
        } for x in cons[:8]]

        return {
            "variant":f"{chrom}:{pos} {ref}>{alt}","consequence":c.get("consequence_terms",[]),
            "impact":c.get("impact",""),"hgvsc":c.get("hgvsc",""),"hgvsp":c.get("hgvsp",""),
            "gene_symbol":c.get("gene_symbol",c.get("gene_id","")),"transcript_id":c.get("transcript_id",""),"biotype":c.get("biotype",""),
            "polyphen_score":pp,"polyphen_prediction":pp_pred,"polyphen_interpretation":interpret_polyphen(pp),
            "sift_score":sift,"sift_prediction":sift_pred,"sift_interpretation":interpret_sift(sift),
            "cadd_raw":cadd_r,"cadd_phred":cadd_p,"cadd_interpretation":interpret_cadd(cadd_p),
            "overall_pathogenicity":compute_overall_score(pp,sift,cadd_p),
            "all_transcripts":all_t,"api_url":url,"assembly":assembly,
        }
    except requests.Timeout:
        return {"error":"Délai dépassé (Ensembl VEP). Réessayez dans quelques secondes."}
    except Exception as e:
        return {"error":f"Erreur: {str(e)}"}


def interpret_polyphen(s):
    if s is None: return "Non disponible"
    if s>=0.908: return "Probablement délétère (Probably damaging)"
    if s>=0.447: return "Possiblement délétère (Possibly damaging)"
    return "Bénin (Benign)"

def interpret_sift(s):
    if s is None: return "Non disponible"
    return "Délétère (Deleterious)" if s<0.05 else "Toléré (Tolerated)"

def interpret_cadd(p):
    if p is None: return "Non calculé"
    if p>=30: return "Top 0.1% variants les plus délétères"
    if p>=20: return "Top 1% — potentiellement pathogène"
    if p>=15: return "Suspect — évaluation complémentaire"
    return "Score faible — probable variant bénin"

def compute_overall_score(pp,sift,cadd):
    score=0; factors=[]
    if pp is not None:
        if pp>=0.908: score+=2; factors.append(f"PolyPhen-2: {pp:.3f} — probablement délétère (PP3 ACMG)")
        elif pp>=0.447: score+=1; factors.append(f"PolyPhen-2: {pp:.3f} — possiblement délétère")
    if sift is not None:
        if sift<0.05: score+=2; factors.append(f"SIFT: {sift:.4f} — délétère (PP3 ACMG)")
    if cadd is not None:
        if cadd>=30: score+=3; factors.append(f"CADD Phred: {cadd:.1f} ≥30 (PP3 ACMG — très délétère)")
        elif cadd>=20: score+=2; factors.append(f"CADD Phred: {cadd:.1f} ≥20 — délétère")
        elif cadd>=15: score+=1; factors.append(f"CADD Phred: {cadd:.1f} ≥15 — suspect")
    cats={6:"Probablement Pathogène",4:"Possiblement Pathogène",2:"VUS (Variant d'Incertitude)",0:"Probablement Bénin"}
    cat=next(v for k,v in sorted(cats.items(),reverse=True) if score>=k)
    return {"score":score,"max":7,"category":cat,"factors":factors}


def classify_acmg(criteria):
    pvs=1 if criteria.get("PVS1") else 0
    ps=sum(criteria.get(f"PS{i}",False) for i in range(1,5))
    pm=sum(criteria.get(f"PM{i}",False) for i in range(1,7))
    pp=sum(criteria.get(f"PP{i}",False) for i in range(1,6))
    ba=1 if criteria.get("BA1") else 0
    bs=sum(criteria.get(f"BS{i}",False) for i in range(1,5))
    bp=sum(criteria.get(f"BP{i}",False) for i in range(1,8))
    cl="VUS"; ev="Incertain"
    if ba==1: cl,ev="Bénin","Autonome"
    elif bs>=2: cl,ev="Bénin","Fort"
    elif (bs==1 and bp>=1) or bp>=2: cl,ev="Probablement Bénin","Supportif"
    elif (pvs==1 and ps>=1) or ps>=2 or (ps==1 and pm>=3) or (pvs==1 and pm>=2): cl,ev="Pathogène","Fort"
    elif (pvs==1 and pm==0 and ps==0) or (ps==1 and pm<=1) or pm>=3 or (pm==2 and pp>=2): cl,ev="Probablement Pathogène","Modéré"
    recs={"Pathogène":"⚠️ Variant pathogène confirmé. Conseil génétique obligatoire.","Probablement Pathogène":"⚠️ Variant probablement pathogène. Suivi renforcé et reclassification progressive.","VUS":"❓ VUS. Ne pas utiliser seul pour décisions cliniques.","Probablement Bénin":"✅ Probablement bénin.","Bénin":"✅ Variant bénin."}
    return {"classification":cl,"evidence_level":ev,"criteria_active":[k for k,v in criteria.items() if v],"score_summary":{"PVS":pvs,"PS":ps,"PM":pm,"PP":pp,"BA":ba,"BS":bs,"BP":bp},"recommendation":recs.get(cl,""),"reference":"Richards S et al. Genetics in Medicine 2015;17:405 (PMID 25741868)","reference_url":"https://pubmed.ncbi.nlm.nih.gov/25741868/"}


HEREDITARY_SYNDROMES={
    "BRCA1/2 — Sein & Ovaire":{"genes":["BRCA1","BRCA2"],"criteria":[{"id":"c1","label":"Cancer du sein < 50 ans","weight":15},{"id":"c2","label":"Cancer du sein bilatéral","weight":20},{"id":"c3","label":"Cancer de l'ovaire (tout âge)","weight":25},{"id":"c4","label":"Cancer du sein homme","weight":30},{"id":"c5","label":"≥2 parents 1er degré atteints","weight":20},{"id":"c6","label":"Origine Ashkénaze","weight":10},{"id":"c7","label":"Triple négatif < 60 ans","weight":15},{"id":"c8","label":"Cancer pancréas familial","weight":10}],"thresholds":{"low":20,"moderate":40,"high":60},"carrier_risk":{"BRCA1 sein":"55-72%","BRCA1 ovaire":"44%","BRCA2 sein":"45-69%","BRCA2 ovaire":"17%"},"guidelines":"NCCN Guidelines v2.2024"},
    "Lynch — Colorectal héréditaire":{"genes":["MLH1","MSH2","MSH6","PMS2","EPCAM"],"criteria":[{"id":"l1","label":"Cancer colorectal < 50 ans","weight":20},{"id":"l2","label":"≥3 parents atteints Amsterdam","weight":35},{"id":"l3","label":"MSI-H ou déficit MMR","weight":40},{"id":"l4","label":"Cancer endomètre < 50 ans","weight":20},{"id":"l5","label":"Cancer synchrone/métachrone","weight":15},{"id":"l6","label":"Parent Lynch confirmé","weight":50}],"thresholds":{"low":15,"moderate":35,"high":55},"carrier_risk":{"Colorectal":"40-80%","Endomètre":"25-60%"},"guidelines":"Amsterdam II / Bethesda / NCCN"},
    "Li-Fraumeni — TP53":{"genes":["TP53"],"criteria":[{"id":"lf1","label":"Sarcome < 45 ans","weight":30},{"id":"lf2","label":"Cancer parent < 45 ans","weight":25},{"id":"lf3","label":"Tumeur cérébrale","weight":20},{"id":"lf4","label":"Cancer sein < 31 ans","weight":25},{"id":"lf5","label":"Carcinome corticosurrénalien","weight":35},{"id":"lf6","label":"Leucémie / MDS","weight":15}],"thresholds":{"low":20,"moderate":40,"high":60},"carrier_risk":{"Cancer lifetime":"~90%","Sein":"54%","Sarcome":"22%"},"guidelines":"Chompret 2015 / NCCN"},
    "MEN1 — Néoplasies endocrines":{"genes":["MEN1"],"criteria":[{"id":"m1","label":"Tumeur parathyroïde","weight":30},{"id":"m2","label":"Tumeur neuroendocrine pancréas","weight":30},{"id":"m3","label":"Adénome hypophysaire","weight":30},{"id":"m4","label":"2+ tumeurs MEN1","weight":50},{"id":"m5","label":"Parent MEN1 confirmé","weight":40}],"thresholds":{"low":15,"moderate":35,"high":55},"carrier_risk":{"MEN1 clinique":"~95% à 50 ans"},"guidelines":"Thakker et al. 2012"},
    "FAP — Polypose (APC)":{"genes":["APC"],"criteria":[{"id":"a1","label":"≥100 polypes adénomateux","weight":50},{"id":"a2","label":"Polypose familiale confirmée","weight":40},{"id":"a3","label":"Tumeur desmoïde","weight":20},{"id":"a4","label":"Ostéomes / anomalies dentaires","weight":15},{"id":"a5","label":"Cancer colorectal < 40 ans","weight":25}],"thresholds":{"low":15,"moderate":35,"high":55},"carrier_risk":{"Colorectal FAP":"~100% si non traité"},"guidelines":"NCCN / ESMO FAP"},
}

def calculate_hereditary_risk(syndrome_name,selected_criteria):
    if syndrome_name not in HEREDITARY_SYNDROMES: return {"error":f"Syndrome inconnu"}
    syn=HEREDITARY_SYNDROMES[syndrome_name]
    total=sum(c["weight"] for c in syn["criteria"] if c["id"] in selected_criteria)
    mp=sum(c["weight"] for c in syn["criteria"])
    norm=min(100,round(total/mp*100,1))
    th=syn["thresholds"]
    if norm<th["low"]: lv,co,rc="Faible","green","Surveillance standard."
    elif norm<th["moderate"]: lv,co,rc="Modéré","orange","Consultation oncogénétique recommandée."
    elif norm<th["high"]: lv,co,rc="Élevé","red","Test génétique recommandé. Conseil génétique familial."
    else: lv,co,rc="Très élevé","darkred","Test génétique et prise en charge immédiate."
    return {"syndrome":syndrome_name,"genes":syn["genes"],"score":norm,"risk_level":lv,"color":co,"recommendation":rc,"matched_criteria":[c for c in syn["criteria"] if c["id"] in selected_criteria],"carrier_risk":syn.get("carrier_risk",{}),"guidelines":syn.get("guidelines",""),"criteria_available":syn["criteria"]}

def get_all_syndromes():
    return [{"name":n,"genes":s["genes"]} for n,s in HEREDITARY_SYNDROMES.items()]
