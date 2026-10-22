#!/usr/bin/env python3
"""RDI: non-destructive, tentative music programming preview.

Reads existing SQLite measurements. Never changes AzuraCast or music files.
Outputs proposals only when enough indicators agree; manual review still required.
"""
import argparse
import collections
import pathlib
import sqlite3

DB=pathlib.Path.home()/"rdi-music"/"music.db"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--limit",type=int,default=30)
    args=p.parse_args()
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    query="""SELECT t.path,t.rms,t.peak,f.integrated_lufs,f.loudness_range,
                    r.bpm_candidate,r.beat_score,r.energy_variation
              FROM tracks t
              LEFT JOIN track_features f ON f.path=t.path AND f.size=t.size AND f.modified=t.modified
              LEFT JOIN track_rhythm r ON r.path=t.path AND r.size=t.size AND r.modified=t.modified
              ORDER BY t.analyzed_at ASC"""
    rows=con.execute(query).fetchall()
    groups=collections.Counter()
    print("ANTEPRIMA RDI — proposte NON applicate alle playlist")
    print("Le etichette dipendono da euristiche, non dal riconoscimento del genere o delle emozioni.")
    seen=0
    for row in rows:
        if seen>=args.limit: break
        name=pathlib.Path(row["path"]).stem[:45]
        lufs=row["integrated_lufs"]; bpm=row["bpm_candidate"]
        score=row["beat_score"]; dynamic=row["loudness_range"]
        if lufs is None or score is None:
            category="IN ATTESA DI ANALISI"
            reason="misure incomplete"
        elif bpm is None or score<0.30:
            category="DA ASCOLTARE"
            reason="ritmo incerto"
        elif bpm>=120 and lufs>=-17 and dynamic<=9 and score>=0.40:
            category="CANDIDATO RITMATO"
            reason="impulsi frequenti, sonorita elevata"
        elif bpm<=80 and lufs<=-15 and score>=0.35:
            category="CANDIDATO TRANQUILLO"
            reason="impulsi radi, sonorita moderata"
        else:
            category="DA ASCOLTARE"
            reason="indicatori non concordi"
        groups[category]+=1
        print(f"{category:<23} | {name:<45} | {reason}")
        seen+=1
    print("\nRiepilogo campione:")
    for k,n in groups.items(): print(f"- {k}: {n}")
    print(f"Mostrati: {seen}; censiti nel database: {len(rows)}")
    print("Nessuna playlist, spot o podcast modificato.")
if __name__=="__main__":main()
