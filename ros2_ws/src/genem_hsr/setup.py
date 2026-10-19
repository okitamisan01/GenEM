from setuptools import find_packages, setup
setup(name='genem_hsr', version='0.1.0', packages=find_packages(exclude=['test']),
      data_files=[('share/ament_index/resource_index/packages', ['resource/genem_hsr']),
                  ('share/genem_hsr', ['package.xml'])],
      install_requires=['setuptools', 'PyYAML', 'requests'], zip_safe=True,
      maintainer='GenEM contributors', maintainer_email='maintainers@example.com',
      description='GenEM-inspired validated mock behavior prototype',
      license='BSD-3-Clause', tests_require=['pytest'], entry_points={})
