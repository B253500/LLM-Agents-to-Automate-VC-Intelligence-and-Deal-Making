import nltk

packages_to_download = ['punkt', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']

print("Downloading required NLTK packages...")
for package in packages_to_download:
    print(f"Downloading '{package}'...")
    nltk.download(package)
    
print("All NLTK downloads complete.")
