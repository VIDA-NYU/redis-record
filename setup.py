import setuptools

setuptools.setup(
    name='redis_record',
    version='0.0.1',
    description='redis streams library',
    long_description=open('README.md').read().strip(),
    long_description_content_type='text/markdown',
    author='Bea Steers',
    author_email='bea.steers@gmail.com',
    url=f'https://github.com/VIDA-NYU/redis-streamer',
    packages=setuptools.find_packages(),
    entry_points={'console_scripts': ['redisstreamer=redis_streamer.cli:main']},
    install_requires=[
        'redis', 'mcap', 'orjson', 'tqdm', 'fire',
    ],
    extras_require={},
    license='MIT License',
    keywords='redis record streams video streaming')
