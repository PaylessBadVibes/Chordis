"""
Seed initial tutorial data for Music Corner
Run this script to populate the database with beginner, intermediate, and advanced tutorials
"""

from api import app
from models import db, Tutorial
from datetime import datetime

def seed_tutorials():
    with app.app_context():
        print("Seeding tutorials...")
        
        # Clear existing tutorials (optional - comment out to keep existing)
        # Tutorial.query.delete()
        # db.session.commit()
        
        tutorials = [
            # ==================== BEGINNER TUTORIALS ====================
            Tutorial(
                title="What Are Guitar Chords?",
                description="Learn the basics of guitar chords, what they are, and why they're essential to playing music.",
                content_type="video",
                skill_level="beginner",
                video_url="https://www.youtube.com/watch?v=BCBcy3CSIAs",
                thumbnail="https://img.youtube.com/vi/BCBcy3CSIAs/maxresdefault.jpg",
                duration=10,
                order=1,
                content="""
                <h2>Introduction to Guitar Chords</h2>
                <p>A chord is when you play multiple notes together to create harmony. In this tutorial, you'll learn:</p>
                <ul>
                    <li>What makes up a chord</li>
                    <li>How chords are named</li>
                    <li>The difference between major and minor chords</li>
                    <li>How to read chord diagrams</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Your First 3 Chords: C, G, and D",
                description="Start your guitar journey by learning the three most essential beginner chords that unlock hundreds of songs.",
                content_type="video",
                skill_level="beginner",
                video_url="https://www.youtube.com/watch?v=cnyeD-hov5s",
                thumbnail="https://img.youtube.com/vi/cnyeD-hov5s/maxresdefault.jpg",
                duration=12,
                order=2,
                content="""
                <h2>The Essential Three Chords</h2>
                <p>These three chords (C, G, and D) are the foundation of countless songs. Master these and you'll be playing real music in no time!</p>
                <h3>What You'll Learn:</h3>
                <ul>
                    <li>Proper finger placement for each chord</li>
                    <li>How to switch between chords smoothly</li>
                    <li>Common songs that use these chords</li>
                    <li>Practice exercises to build muscle memory</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="How to Read Guitar Tablature (TAB)",
                description="Tablature is the easiest way to learn songs on guitar. Learn how to read TAB notation step by step.",
                content_type="text",
                skill_level="beginner",
                duration=10,
                order=3,
                content="""
                <h2>Understanding Guitar Tablature</h2>
                <p>Tablature (or TAB) is a simple way to read music specifically for guitar. Instead of traditional sheet music, TAB shows you exactly where to place your fingers.</p>
                
                <h3>How TAB Works:</h3>
                <p>TAB has 6 lines representing the 6 strings on your guitar:</p>
                <pre style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; font-family: monospace;">
e|---0---1---3---
B|---1---1---0---
G|---0---2---0---
D|---2---3---0---
A|---3---3---2---
E|---x---x---3---
    C   F   G
                </pre>
                
                <h3>Reading TAB:</h3>
                <ul>
                    <li><strong>Numbers:</strong> Tell you which fret to press (0 = open string)</li>
                    <li><strong>x:</strong> Don't play this string</li>
                    <li><strong>Lines:</strong> Represent strings (top = thinnest, bottom = thickest)</li>
                </ul>
                
                <h3>Practice:</h3>
                <p>Try playing the C, F, and G chords shown above by following the numbers!</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Basic Strumming Patterns for Beginners",
                description="Learn simple strumming patterns that work with almost any song. Perfect for absolute beginners!",
                content_type="video",
                skill_level="beginner",
                video_url="https://www.youtube.com/watch?v=4-hOy2tHR7Q",
                thumbnail="https://img.youtube.com/vi/4-hOy2tHR7Q/maxresdefault.jpg",
                duration=15,
                order=4,
                content="""
                <h2>Strumming 101</h2>
                <p>Strumming is how you create rhythm on guitar. Start with these simple patterns:</p>
                <h3>Pattern 1: Down Strums Only</h3>
                <p>Count: 1, 2, 3, 4 (strum down on each beat)</p>
                
                <h3>Pattern 2: Down-Down-Up-Up-Down-Up</h3>
                <p>This is one of the most versatile patterns for beginners!</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Tuning Your Guitar",
                description="Learn how to tune your guitar using standard tuning (E-A-D-G-B-e). Essential skill for every guitarist!",
                content_type="interactive",
                skill_level="beginner",
                duration=5,
                order=5,
                content="""
                <h2>Standard Guitar Tuning</h2>
                <p>From thickest to thinnest string:</p>
                <ul>
                    <li>6th String: E (82.41 Hz)</li>
                    <li>5th String: A (110.00 Hz)</li>
                    <li>4th String: D (146.83 Hz)</li>
                    <li>3rd String: G (196.00 Hz)</li>
                    <li>2nd String: B (246.94 Hz)</li>
                    <li>1st String: e (329.63 Hz)</li>
                </ul>
                <p><strong>Tip:</strong> Use the Chord Tools panel in ChordAI to hear reference pitches!</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Common Chord Progressions",
                description="Discover the most popular chord progressions used in thousands of hit songs.",
                content_type="text",
                skill_level="beginner",
                duration=12,
                order=6,
                content="""
                <h2>Popular Chord Progressions</h2>
                <p>These progressions appear in countless songs across all genres:</p>
                
                <h3>1. The "Pop" Progression: C - G - Am - F</h3>
                <p>Songs: Let It Be (Beatles), Someone Like You (Adele), With or Without You (U2)</p>
                
                <h3>2. The "50s" Progression: C - Am - F - G</h3>
                <p>Songs: Stand By Me, Blue Moon, Unchained Melody</p>
                
                <h3>3. The "12-Bar Blues": I - IV - I - V</h3>
                <p>Foundation of blues, rock, and jazz music</p>
                
                <h3>Practice Tip:</h3>
                <p>Try playing each progression slowly, focusing on smooth chord changes!</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Finger Exercises for Beginners",
                description="Build finger strength and dexterity with these simple daily exercises. Just 5-10 minutes a day!",
                content_type="video",
                skill_level="beginner",
                video_url="https://www.youtube.com/watch?v=nvXYbFCKKqQ",
                thumbnail="https://img.youtube.com/vi/nvXYbFCKKqQ/maxresdefault.jpg",
                duration=10,
                order=7,
                is_published=True
            ),
            
            Tutorial(
                title="How to Hold a Guitar Pick",
                description="Proper pick grip is essential for good technique. Learn the correct way to hold and use a guitar pick.",
                content_type="text",
                skill_level="beginner",
                duration=5,
                order=8,
                content="""
                <h2>Pick Holding Technique</h2>
                <p>Holding a pick correctly improves your tone and makes playing easier.</p>
                
                <h3>The Standard Grip:</h3>
                <ol>
                    <li>Make a loose fist with your picking hand</li>
                    <li>Extend your index finger</li>
                    <li>Place the pick on top of your index finger</li>
                    <li>Use your thumb to hold it in place</li>
                    <li>Let only a small tip of the pick show (2-3mm)</li>
                </ol>
                
                <h3>Key Points:</h3>
                <ul>
                    <li>Keep your grip relaxed, not tight</li>
                    <li>The pick should be at a slight angle, not perfectly flat</li>
                    <li>Experiment to find what feels comfortable</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Playing Your First Song",
                description="Put everything together and play a complete song! We'll start with a simple 3-chord song.",
                content_type="video",
                skill_level="beginner",
                video_url="https://www.youtube.com/watch?v=BqV53z-dGyA",
                thumbnail="https://img.youtube.com/vi/BqV53z-dGyA/maxresdefault.jpg",
                duration=20,
                order=9,
                content="""
                <h2>Your First Complete Song</h2>
                <p>Congratulations on making it this far! Now let's play a real song using what you've learned.</p>
                <p>We'll use: C, G, and Am chords with a simple down-strum pattern.</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Understanding Music Rhythm",
                description="Learn about beats, time signatures, and rhythm - the foundation of all music.",
                content_type="text",
                skill_level="beginner",
                duration=15,
                order=10,
                content="""
                <h2>Music Rhythm Basics</h2>
                <p>Rhythm is what makes music move and groove!</p>
                
                <h3>Understanding Beats:</h3>
                <p>A beat is the basic unit of time in music. When you tap your foot to music, you're feeling the beat.</p>
                
                <h3>Time Signatures:</h3>
                <p><strong>4/4 Time (Common Time):</strong> Most popular songs use this - 4 beats per measure</p>
                <p><strong>3/4 Time (Waltz Time):</strong> 3 beats per measure, sounds like "ONE-two-three, ONE-two-three"</p>
                
                <h3>Counting Rhythm:</h3>
                <p>Count "1, 2, 3, 4" repeatedly while strumming - each number is one beat!</p>
                """,
                is_published=True
            ),
            
            # ==================== INTERMEDIATE TUTORIALS ====================
            Tutorial(
                title="Mastering Barre Chords",
                description="Unlock the entire fretboard by learning barre chords. A crucial technique for intermediate players.",
                content_type="video",
                skill_level="intermediate",
                video_url="https://www.youtube.com/watch?v=NU1e9KfKYcM",
                thumbnail="https://img.youtube.com/vi/NU1e9KfKYcM/maxresdefault.jpg",
                duration=18,
                order=11,
                content="""
                <h2>Barre Chord Mastery</h2>
                <p>Barre chords allow you to play any chord anywhere on the neck!</p>
                <h3>What You'll Learn:</h3>
                <ul>
                    <li>F Major barre chord (the foundation)</li>
                    <li>Building finger strength</li>
                    <li>Moving barre shapes up the neck</li>
                    <li>Common barre chord patterns</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Music Theory: Keys and Scales",
                description="Understand keys, scales, and how they relate to chord progressions. Essential theory for songwriting.",
                content_type="text",
                skill_level="intermediate",
                duration=25,
                order=12,
                content="""
                <h2>Keys and Scales Explained</h2>
                
                <h3>What is a Key?</h3>
                <p>A key is a group of chords that sound good together. For example, the key of C Major contains these chords:</p>
                <ul>
                    <li>C Major</li>
                    <li>D minor</li>
                    <li>E minor</li>
                    <li>F Major</li>
                    <li>G Major</li>
                    <li>A minor</li>
                    <li>B diminished</li>
                </ul>
                
                <h3>The Major Scale:</h3>
                <p>C Major scale: C - D - E - F - G - A - B - C</p>
                <p>Pattern: Whole - Whole - Half - Whole - Whole - Whole - Half</p>
                
                <h3>Why This Matters:</h3>
                <p>Understanding keys helps you:</p>
                <ul>
                    <li>Write your own songs</li>
                    <li>Improvise solos</li>
                    <li>Transpose songs to different keys</li>
                    <li>Understand music theory</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Fingerpicking Basics",
                description="Move beyond strumming! Learn fingerpicking patterns to add beautiful textures to your playing.",
                content_type="video",
                skill_level="intermediate",
                video_url="https://www.youtube.com/watch?v=r9jnMwpRu-I",
                thumbnail="https://img.youtube.com/vi/r9jnMwpRu-I/maxresdefault.jpg",
                duration=20,
                order=13,
                content="""
                <h2>Introduction to Fingerpicking</h2>
                <p>Fingerpicking creates beautiful, intricate patterns by plucking individual strings.</p>
                <h3>Basic Pattern:</h3>
                <p>Thumb (p): Bass strings (E, A, D)<br>
                Index (i): G string<br>
                Middle (m): B string<br>
                Ring (a): high e string</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Power Chords for Rock Music",
                description="Learn power chords - the backbone of rock, punk, and metal music. Simple but powerful!",
                content_type="video",
                skill_level="intermediate",
                video_url="https://www.youtube.com/watch?v=YfWFgCCW31M",
                thumbnail="https://img.youtube.com/vi/YfWFgCCW31M/maxresdefault.jpg",
                duration=15,
                order=14,
                content="""
                <h2>Power Chords Explained</h2>
                <p>Power chords use only 2-3 notes and sound amazing with distortion!</p>
                <h3>What You'll Learn:</h3>
                <ul>
                    <li>How to form a power chord</li>
                    <li>Moving power chords up the neck</li>
                    <li>Palm muting technique</li>
                    <li>Famous riffs using power chords</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Advanced Strumming Techniques",
                description="Take your rhythm playing to the next level with syncopation, muting, and dynamic control.",
                content_type="video",
                skill_level="intermediate",
                video_url="https://www.youtube.com/watch?v=vWTOhXDVuC8",
                thumbnail="https://img.youtube.com/vi/vWTOhXDVuC8/maxresdefault.jpg",
                duration=22,
                order=15,
                is_published=True
            ),
            
            # ==================== ADVANCED TUTORIALS ====================
            Tutorial(
                title="Jazz Chord Voicings",
                description="Explore sophisticated jazz chord voicings including 7ths, 9ths, 11ths, and altered dominants.",
                content_type="video",
                skill_level="advanced",
                video_url="https://www.youtube.com/watch?v=qObghOtMcXc",
                thumbnail="https://img.youtube.com/vi/qObghOtMcXc/maxresdefault.jpg",
                duration=30,
                order=16,
                content="""
                <h2>Jazz Harmony</h2>
                <p>Jazz uses extended chords to create rich, complex harmonies.</p>
                <h3>Chord Extensions:</h3>
                <ul>
                    <li>Major 7th chords (Cmaj7)</li>
                    <li>Dominant 7th chords (G7)</li>
                    <li>Minor 7th chords (Am7)</li>
                    <li>9th, 11th, and 13th extensions</li>
                </ul>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Fingerstyle Techniques: Travis Picking",
                description="Master Travis picking, an advanced fingerstyle technique used in country, folk, and blues.",
                content_type="video",
                skill_level="advanced",
                video_url="https://www.youtube.com/watch?v=J7Tb0aKzUGE",
                thumbnail="https://img.youtube.com/vi/J7Tb0aKzUGE/maxresdefault.jpg",
                duration=25,
                order=17,
                content="""
                <h2>Travis Picking Pattern</h2>
                <p>Named after Merle Travis, this technique creates a steady bass line while playing melody on top.</p>
                <h3>The Pattern:</h3>
                <p>Thumb alternates between bass notes while fingers pluck higher strings in a syncopated pattern.</p>
                """,
                is_published=True
            ),
            
            Tutorial(
                title="Song Composition: Writing Your Own Music",
                description="Learn the art of songwriting - from chord progressions to melody, lyrics, and song structure.",
                content_type="text",
                skill_level="advanced",
                duration=35,
                order=18,
                content="""
                <h2>Songwriting Fundamentals</h2>
                
                <h3>Song Structure:</h3>
                <p>Most songs follow these common structures:</p>
                <ul>
                    <li><strong>Verse-Chorus-Verse-Chorus-Bridge-Chorus</strong> (Pop/Rock)</li>
                    <li><strong>AABA</strong> (Jazz Standard)</li>
                    <li><strong>Verse-Verse-Chorus</strong> (Folk)</li>
                </ul>
                
                <h3>Creating Chord Progressions:</h3>
                <p>Start with a key and experiment with the chords in that key. Common techniques:</p>
                <ul>
                    <li>I-V-vi-IV progression (very popular in pop)</li>
                    <li>ii-V-I progression (jazz)</li>
                    <li>i-VII-VI-V (minor key rock)</li>
                </ul>
                
                <h3>Melody Writing:</h3>
                <p>Your melody should complement the chords. Tips:</p>
                <ul>
                    <li>Use notes from the underlying chord</li>
                    <li>Create contrast between verse and chorus</li>
                    <li>Use repetition and variation</li>
                    <li>Think about the natural rhythm of words (for lyrics)</li>
                </ul>
                
                <h3>Lyrics:</h3>
                <p>Good lyrics tell a story or convey emotion. Consider:</p>
                <ul>
                    <li>Personal experiences</li>
                    <li>Metaphors and imagery</li>
                    <li>Rhyme schemes (AABB, ABAB, ABCB)</li>
                    <li>Syllable count for smooth singing</li>
                </ul>
                
                <h3>Getting Started:</h3>
                <p>1. Choose a chord progression you like<br>
                2. Hum melodies over it until something sticks<br>
                3. Add lyrics that fit the melody<br>
                4. Refine and polish</p>
                """,
                is_published=True
            ),
        ]
        
        # Add all tutorials to database
        for tutorial in tutorials:
            db.session.add(tutorial)
        
        db.session.commit()
        
        print(f"[OK] Successfully seeded {len(tutorials)} tutorials!")
        print(f"   - Beginner: {len([t for t in tutorials if t.skill_level == 'beginner'])}")
        print(f"   - Intermediate: {len([t for t in tutorials if t.skill_level == 'intermediate'])}")
        print(f"   - Advanced: {len([t for t in tutorials if t.skill_level == 'advanced'])}")

if __name__ == "__main__":
    seed_tutorials()

